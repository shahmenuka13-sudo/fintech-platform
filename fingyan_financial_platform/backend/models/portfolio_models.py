from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class HoldingAsset(BaseModel):
    symbol: str = Field(..., description="Stock symbol, e.g., RELIANCE.NS")
    quantity: float = Field(..., gt=0, description="Number of shares held")
    average_buy_price: float = Field(..., ge=0, description="Average price at which the asset was bought")
    # last_transaction_date: Optional[datetime] = None # Could be useful later

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Name of the portfolio")
    description: Optional[str] = Field(None, max_length=500, description="Optional description for the portfolio")
    # user_id: int # This will be added once authentication is in place

class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    # holdings: Optional[List[HoldingAsset]] = None # Full replacement of holdings, or use separate endpoints for managing holdings

class PortfolioResponse(PortfolioCreate):
    id: int
    user_id: int # For now, can be a dummy or placeholder
    created_at: datetime
    updated_at: datetime
    holdings: List[HoldingAsset] = [] # Current holdings in the portfolio
    # calculated_total_value: Optional[float] = None # This would be calculated on the fly

# For adding/updating assets within a portfolio
class PortfolioAssetUpdate(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: float = Field(..., gt=0, description="New quantity of shares. If removing, use a specific remove endpoint or set to 0 if logic supports.")
    average_buy_price: float = Field(..., ge=0, description="New average buy price for this asset in the portfolio.")
    # transaction_type: str # "buy" or "sell" - could be more granular for advanced transaction logging

class PortfolioAssetResponse(HoldingAsset):
    portfolio_id: int
    # last_updated: datetime # When this specific asset was last updated in the portfolio

# For calculating portfolio value, linking with market data
class EnrichedHoldingAsset(HoldingAsset):
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None

class PortfolioDetailResponse(PortfolioResponse):
    holdings: List[EnrichedHoldingAsset] = []
    total_invested_value: float = 0.0
    current_total_value: float = 0.0
    overall_profit_loss: float = 0.0
    overall_profit_loss_percent: float = 0.0
