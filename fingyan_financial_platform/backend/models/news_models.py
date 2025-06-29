from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class NewsArticle(BaseModel):
    uuid: Optional[str] = None # Unique ID from source if available
    title: str
    link: HttpUrl # URL to the full article
    publisher: Optional[str] = None # Source of the news, e.g., "Reuters", "Moneycontrol"
    provider_publish_time: Optional[datetime] = None # Timestamp from the provider
    # type: Optional[str] = None # E.g. "STORY", "BRIEF" from yfinance

    summary: Optional[str] = None # Optional AI-generated summary
    # sentiment_score: Optional[float] = None # Optional AI-generated sentiment
    # sentiment_label: Optional[str] = None # e.g., "positive", "negative", "neutral"
    # related_tickers: Optional[List[str]] = None # Tickers mentioned or related

    class Config:
        orm_mode = True # In case we ever store these and read them back

class NewsResponse(BaseModel):
    symbol: Optional[str] = None # If news is specific to a ticker
    articles: List[NewsArticle]
    source_info: Optional[str] = "Aggregated from various sources" # Info about data provider(s)
