from pydantic import BaseModel, Field, validator
from typing import Optional, Union, Literal
from datetime import datetime

class AlertConditionBase(BaseModel):
    # Example: price_greater_than, price_less_than, rsi_above, macd_cross_bullish
    indicator: str = Field(..., description="Technical indicator or 'price'")
    # value: Union[float, str] # Target value for the indicator (e.g., 70 for RSI, or a price level)
    # More specific condition types might be better

class PriceAlertCondition(AlertConditionBase):
    indicator: Literal["price"] = "price"
    operator: Literal["greater_than_or_equal_to", "less_than_or_equal_to"] # More specific than just gt/lt
    target_value: float

class IndicatorAlertCondition(AlertConditionBase):
    # For simplicity, not detailing specific indicators like RSI, MACD here yet.
    # This would require more complex validation and parameters per indicator.
    # E.g. for RSI: indicator="RSI", period=14, value_above=70
    indicator: str # e.g., "RSI", "MACD_signal_cross"
    parameters: Optional[dict] = Field(None, description="Parameters for the indicator, e.g., {'period': 14}")
    comparison_operator: Literal["above", "below", "crosses_above", "crosses_below"] # Or similar
    threshold_value: Union[float, str] # e.g., 70 for RSI, or another series like 'SMA50'

class AlertBase(BaseModel):
    symbol: str = Field(..., description="Stock/asset symbol for the alert, e.g., RELIANCE.NS")
    # condition: Union[PriceAlertCondition, IndicatorAlertCondition] # This makes validation complex
    # Simplified condition for now:
    alert_type: Literal["price", "indicator"] = "price" # Default to price alerts
    description: Optional[str] = Field(None, description="User-defined description for the alert")

    # For price alerts:
    target_price: Optional[float] = None
    trigger_when_above: Optional[bool] = Field(None, description="True to trigger if price > target, False if price < target. One must be set if target_price is set.")

    # For more generic indicator alerts (conceptual for now)
    # indicator_name: Optional[str] = None # e.g., "RSI_14"
    # indicator_condition: Optional[str] = None # e.g., "crosses_above_70"

    is_active: bool = Field(True, description="Is the alert currently active and being monitored?")
    # user_id will be added from context (e.g. authenticated user)

class AlertCreate(AlertBase):
    @validator('target_price', always=True)
    def check_target_price_and_condition(cls, v, values):
        if values.get('alert_type') == 'price':
            if v is None:
                raise ValueError("target_price is required for price alerts")
            if values.get('trigger_when_above') is None:
                 raise ValueError("trigger_when_above (boolean) must be specified for price alerts (True for above, False for below)")
        return v

    # Future: Add validator for indicator_name/condition if alert_type == 'indicator'

class AlertUpdate(BaseModel):
    # Allow updating only specific fields, e.g., target price or active status
    target_price: Optional[float] = None
    trigger_when_above: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class AlertResponse(AlertBase):
    id: int
    user_id: int
    created_at: datetime
    triggered_at: Optional[datetime] = None # When the alert was last triggered
    # last_checked_at: Optional[datetime] = None # When the alert condition was last evaluated

    class Config:
        orm_mode = True # For easy conversion from SQLAlchemy model if fields match closely.
                        # Manual mapping is often safer for complex cases.
