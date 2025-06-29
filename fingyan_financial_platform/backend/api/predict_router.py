from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Any
from datetime import datetime, timedelta

from ..models.prediction_models import PredictionRequest, PredictionResponse, TrendPrediction
from ..services import prediction_service # Import the new service
# from ..services.market_data_service import get_latest_close_price # For context if needed

router = APIRouter()

# --- Model Metadata (can be expanded or moved to a config/service) ---
# This provides some basic info about available models.
# In a real system, this could be dynamic or more detailed.
AVAILABLE_MODELS = {
    "prophet_trend_v1": {
        "description": "Trend prediction using Facebook Prophet (daily data, 2-year history).",
        "type": "trend",
        "supported_symbols": "generic", # Indicates it tries to work for any valid yfinance symbol
        "horizon_days_min": 1,
        "horizon_days_max": 30 # Prophet can predict further, but let's cap for API
    }
}
# The DUMMY_MODELS dict below can be removed or merged if prophet_trend_v1 replaces default_trend_v1

# This is a placeholder. Actual model loading and inference would be more complex
# and likely happen in a dedicated service or even a separate microservice.
DUMMY_MODELS = {
    "default_trend_v1": {
        "type": "trend",
        "supported_symbols": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "NIFTYBEES.NS"], # Example
        "horizon_days_min": 1,
        "horizon_days_max": 14
    },
    "price_forecast_lstm_v1": {
        "type": "time_series",
        "supported_symbols": ["RELIANCE.NS"],
        "horizon_days_min": 1,
        "horizon_days_max": 7
    }
}

@router.post("/trend", response_model=PredictionResponse)
async def get_trend_prediction(
    request_data: PredictionRequest = Body(...)
    # model_name: str = Query("prophet_trend_v1", description="Model to use for prediction") # Allow model selection later
):
    """
    Provides a short-term trend prediction for a given stock symbol using a Prophet model.
    """
    model_name = "prophet_trend_v1" # For now, hardcode to use this model.

    if model_name not in AVAILABLE_MODELS or AVAILABLE_MODELS[model_name]["type"] != "trend":
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not found or is not a trend prediction model.")

    model_meta = AVAILABLE_MODELS[model_name]

    # Validate horizon against what the model supports (from metadata)
    if not (model_meta["horizon_days_min"] <= request_data.prediction_horizon_days <= model_meta["horizon_days_max"]):
        raise HTTPException(
            status_code=400,
            detail=f"Prediction horizon {request_data.prediction_horizon_days} days is out of range for model '{model_name}'. "
                   f"Supported: {model_meta['horizon_days_min']}-{model_meta['horizon_days_max']} days."
        )

    # --- Call the Prediction Service ---
    try:
        # The service function `run_prophet_prediction_async` handles yfinance calls and Prophet model.
        # It's designed to be run in a thread pool executor by the service itself.
        trend_direction, confidence_score = await prediction_service.run_prophet_prediction_async(
            symbol=request_data.symbol,
            horizon_days=request_data.prediction_horizon_days
            # history_period can be a default in service or configurable here
        )
    except Exception as e:
        # Catch any unexpected errors from the prediction service call itself
        print(f"Error calling prediction service for {request_data.symbol}: {e}")
        # import traceback
        # traceback.print_exc()
        raise HTTPException(status_code=503, detail=f"Prediction service unavailable or failed for {request_data.symbol}: {str(e)}")

    if trend_direction == "UNCERTAIN" and confidence_score is None:
        # This might indicate an issue within the prediction logic (e.g., insufficient data)
        # Or it could be a valid "uncertain" prediction.
        # For now, return it as is; frontend can interpret.
        # Could also raise 404 or 500 if it means data issue.
        # Let's assume service handles internal errors and "UNCERTAIN" is a valid output.
        pass


    predicted_trend_obj = TrendPrediction(
        direction=trend_direction,
        confidence=confidence_score
    )

    return PredictionResponse(
        symbol=request_data.symbol,
        model_name=model_name, # Could include version from model_meta if available
        generated_at=datetime.utcnow(),
        prediction_horizon_days=request_data.prediction_horizon_days,
        trend=predicted_trend,
        # raw_model_output={"dummy_feature": "example_value", "random_score": rand_val} # Example
    )

# TODO:
# - Add more prediction types (e.g., price forecast, sentiment analysis) as separate endpoints or a unified one.
# - Integrate with actual ML models and a prediction service.
# - Implement caching for predictions if appropriate (e.g., if inputs are common and predictions don't change too rapidly).
# - Secure this endpoint, as ML model inference can be resource-intensive.
# - Consider batch predictions if multiple symbols/requests are common.
# - Add a /models endpoint to list available prediction models and their capabilities.
