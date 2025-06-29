import yfinance as yf
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json # If we were saving models
from typing import Dict, Optional, Tuple, Literal
from datetime import datetime, timedelta
import asyncio # For running Prophet in a thread

# For caching models in memory (simple example)
# A more robust solution might use Redis or a dedicated model store.
# In-memory cache for trained Prophet models (symbol -> {model, timestamp})
# This is very basic and not suitable for production with many symbols or worker processes.
# For a stateless API, models would ideally be loaded from a shared store or retrained.
# Given the current setup, retraining on each call or using a very limited in-memory cache is more feasible.
# Let's skip in-memory model caching for now to keep it stateless and rely on retraining.
# If performance becomes an issue for specific symbols, model caching/saving can be added.

# MODEL_CACHE = {}
# CACHE_EXPIRY_SECONDS = 60 * 60 * 4 # Cache model for 4 hours

async def get_prophet_trend_prediction(
    symbol: str,
    horizon_days: int = 7,
    history_period: str = "2y" # Amount of historical data to train on
) -> Tuple[Literal["UP", "DOWN", "SIDEWAYS", "UNCERTAIN"], Optional[float]]:
    """
    Generates a short-term trend prediction using Facebook Prophet.
    Returns a trend direction and an optional confidence score.

    This function is I/O and CPU bound (yfinance and Prophet training/prediction).
    It should be run in a thread to avoid blocking the main asyncio event loop.
    """

    # ---- 1. Fetch Historical Data (Synchronous yfinance call) ----
    try:
        ticker = yf.Ticker(symbol)
        # Fetch more data for training, e.g., 1-2 years
        hist_df = ticker.history(period=history_period, interval="1d")
        if hist_df.empty:
            print(f"No historical data found for {symbol} with period {history_period}.")
            return "UNCERTAIN", None

        # Prophet requires columns 'ds' (datestamp) and 'y' (value to predict)
        df_prophet = hist_df.reset_index()[['Date', 'Close']].rename(columns={'Date':'ds', 'Close':'y'})
        # Ensure 'ds' is datetime (yf usually returns it as such in index)
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])
        # Remove timezone if present, Prophet works best with naive datetimes
        if df_prophet['ds'].dt.tz is not None:
            df_prophet['ds'] = df_prophet['ds'].dt.tz_localize(None)

        if len(df_prophet) < 30: # Need sufficient data for Prophet
            print(f"Not enough historical data for {symbol} to make a reliable Prophet prediction (need ~30 days, got {len(df_prophet)}).")
            return "UNCERTAIN", None

        last_actual_date = df_prophet['ds'].max()
        last_actual_price = df_prophet[df_prophet['ds'] == last_actual_date]['y'].iloc[0]

    except Exception as e:
        print(f"Error fetching or preparing data for Prophet model ({symbol}): {e}")
        return "UNCERTAIN", None

    # ---- 2. Train Prophet Model & Make Forecast (CPU-bound) ----
    try:
        # Initialize Prophet model
        # Consider adding yearly_seasonality, weekly_seasonality, daily_seasonality based on data frequency and horizon
        # For daily data and short horizon, weekly and yearly might be relevant.
        # Disabling daily_seasonality as we have daily data.
        # Adding country-specific holidays can improve accuracy if relevant (e.g., for India 'IN')
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            # uncertainty_samples=1000 # Default is 1000, reduce for faster fit if needed, but affects confidence interval quality
        )
        # model.add_country_holidays(country_name='IN') # Example for Indian stocks

        model.fit(df_prophet)

        # Create future dataframe for prediction
        future_df = model.make_future_dataframe(periods=horizon_days, freq='D') # 'B' for business days, 'D' for calendar days
        forecast_df = model.predict(future_df)

        # ---- 3. Interpret Forecast for Trend and Confidence ----
        # Compare the predicted price at the end of the horizon with the last actual price.
        predicted_end_price = forecast_df['yhat'].iloc[-1] # Last value in 'yhat' is the furthest prediction

        # Trend direction
        trend_direction: Literal["UP", "DOWN", "SIDEWAYS", "UNCERTAIN"]
        if predicted_end_price > last_actual_price * 1.01: # Define a threshold for "UP" (e.g. >1% change)
            trend_direction = "UP"
        elif predicted_end_price < last_actual_price * 0.99: # Define a threshold for "DOWN" (e.g. <1% change)
            trend_direction = "DOWN"
        else:
            trend_direction = "SIDEWAYS" # Within +/- 1% considered sideways

        # Confidence: Use uncertainty intervals (yhat_lower, yhat_upper)
        # A simple confidence metric: 1 - (width of uncertainty interval / predicted price)
        # This is a heuristic. A more statistically sound confidence would require deeper analysis.
        yhat_lower_end = forecast_df['yhat_lower'].iloc[-1]
        yhat_upper_end = forecast_df['yhat_upper'].iloc[-1]

        confidence_score = None
        if predicted_end_price != 0: # Avoid division by zero
            uncertainty_range = yhat_upper_end - yhat_lower_end
            # Normalize confidence: narrower interval = higher confidence
            # This is a very rough heuristic for "confidence"
            # A value closer to 1 means narrower band relative to price.
            # Cap at reasonable bounds e.g. 0.5 to 0.95
            # Ensure uncertainty_range is not negative (shouldn't happen with Prophet)
            if uncertainty_range >= 0 and predicted_end_price > 0 :
                 # Heuristic: if uncertainty is 10% of price, confidence is 0.9. If 50%, confidence is 0.5.
                 # This needs calibration and is not a true statistical confidence of trend direction.
                 relative_uncertainty = uncertainty_range / predicted_end_price
                 confidence_score = max(0.0, 1.0 - relative_uncertainty * 2) # Scaled and clamped
                 confidence_score = min(0.95, max(0.50, confidence_score)) # Bound between 0.5 and 0.95

        # For debugging:
        # print(f"Symbol: {symbol}, Last Actual: {last_actual_price:.2f} on {last_actual_date.date()}")
        # print(f"Predicted {horizon_days}-day end price: {predicted_end_price:.2f}")
        # print(f"Uncertainty interval: [{yhat_lower_end:.2f}, {yhat_upper_end:.2f}]")
        # print(f"Determined Trend: {trend_direction}, Confidence: {confidence_score}")

        return trend_direction, confidence_score

    except Exception as e:
        print(f"Error during Prophet model training or prediction for {symbol}: {e}")
        # import traceback
        # traceback.print_exc()
        return "UNCERTAIN", None


# Wrapper to run the sync function in a thread, to be called from async FastAPI endpoint
async def run_prophet_prediction_async(
    symbol: str,
    horizon_days: int = 7,
    history_period: str = "2y"
) -> Tuple[Literal["UP", "DOWN", "SIDEWAYS", "UNCERTAIN"], Optional[float]]:
    """
    Asynchronously runs the Prophet trend prediction.
    """
    # Prophet's core C++ Stan components might not be fully thread-safe or GIL-releasing.
    # While asyncio.to_thread is good for I/O-bound or GIL-releasing CPU-bound tasks,
    # heavy CPU tasks that hold the GIL can still block other threads in the same process.
    # For truly scalable CPU-bound tasks, a separate process pool (e.g. ProcessPoolExecutor)
    # or a task queue like Celery with dedicated workers is better.
    # For now, to_thread is a pragmatic first step for a potentially long-running sync function.
    #
    # !! PERFORMANCE NOTE FOR PRODUCTION !!
    # Running Prophet model training and prediction synchronously within a thread pool executor
    # per API call can lead to performance bottlenecks under load:
    # 1. GIL Issues: Heavy CPU-bound Python code like parts of Prophet might still be limited by the GIL,
    #    even in threads.
    # 2. Resource Intensive: Training a model, even Prophet, consumes CPU and memory. Many concurrent
    #    requests can exhaust server resources.
    # 3. Latency: Model training + prediction can take several seconds, impacting API response time.
    #
    # Recommended Production Approaches:
    # - Asynchronous Task Queue: Use Celery or ARQ to offload model training/prediction to background workers.
    #   The API endpoint would submit a task and potentially return a task ID for polling results, or use WebSockets.
    # - Dedicated ML Inference Server: Deploy models using tools like BentoML, NVIDIA Triton Inference Server,
    #   TorchServe, or a custom Flask/FastAPI service scaled independently.
    # - Model Caching/Pre-computation: For popular symbols or common horizons, pre-compute and cache predictions.
    #   Retrain models periodically rather than on-demand for every request.
    # - Simplified Models: For real-time API responses, if complex models are too slow, consider using
    #   pre-trained, lighter models or statistical methods that are faster to compute.

    loop = asyncio.get_running_loop()
    # Using default ThreadPoolExecutor
    result = await loop.run_in_executor(
        None,
        get_prophet_trend_prediction, # The synchronous function to call
        symbol,
        horizon_days,
        history_period
    )
    return result

# Example usage (for testing this service directly):
# async def main_test():
#     symbol_to_test = "RELIANCE.NS"
#     horizon = 7
#     print(f"Requesting Prophet prediction for {symbol_to_test}, {horizon} days ahead...")
#     trend, conf = await run_prophet_prediction_async(symbol_to_test, horizon)
#     print(f"\nFinal Result for {symbol_to_test}: Trend={trend}, Confidence={conf}")

# if __name__ == "__main__":
#     asyncio.run(main_test())
