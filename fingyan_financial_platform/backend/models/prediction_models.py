from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal # Added Literal
from datetime import date, datetime

class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol for which prediction is requested, e.g., RELIANCE.NS")
    # model_name: Optional[str] = Field("default_trend_v1", description="Specify which prediction model to use")
    prediction_horizon_days: Optional[int] = Field(7, ge=1, le=30, description="Number of days into the future for the prediction (e.g., 7 for a week ahead).")
    # additional_features: Optional[Dict[str, Any]] = Field(None, description="Any additional features or context for the model.")

class TrendPrediction(BaseModel):
    direction: Literal["UP", "DOWN", "SIDEWAYS", "UNCERTAIN"]
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score for the prediction, if available.")
    # predicted_price_range_low: Optional[float] = None
    # predicted_price_range_high: Optional[float] = None
    # target_date: Optional[date] = None # The date for which this specific prediction point is valid

class PricePointPrediction(BaseModel):
    timestamp: datetime # Timestamp for the predicted point
    predicted_value: float # Predicted price or value
    lower_bound: Optional[float] = None # For confidence intervals
    upper_bound: Optional[float] = None # For confidence intervals


class PredictionResponse(BaseModel):
    symbol: str
    model_name: str = Field(..., description="Name and version of the model used for this prediction.")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    prediction_horizon_days: int

    # Example for a single trend prediction
    trend: Optional[TrendPrediction] = None

    # Example for a series of price point predictions (e.g., for a chart)
    # time_series_prediction: Optional[List[PricePointPrediction]] = None

    raw_model_output: Optional[Dict[str, Any]] = Field(None, description="Raw output or additional metadata from the model, if any.")
    disclaimer: str = "Predictions are for informational purposes only and not financial advice. Past performance is not indicative of future results."


# For more specific prediction types, you might create more detailed models:
class SentimentAnalysisRequest(BaseModel):
    text_content: str # Could be a news headline, social media post, etc.

class SentimentAnalysisResponse(BaseModel):
    text_content: str
    sentiment_label: Literal["positive", "negative", "neutral"]
    sentiment_score: float = Field(..., ge=-1, le=1, description="Sentiment score, e.g., from -1 (very negative) to +1 (very positive)")
    model_name: str
