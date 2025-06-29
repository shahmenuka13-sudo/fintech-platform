from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class StockTickerInfo(BaseModel):
    symbol: str
    shortName: Optional[str] = None
    longName: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None
    previousClose: Optional[float] = None
    open: Optional[float] = None
    dayHigh: Optional[float] = None
    dayLow: Optional[float] = None
    volume: Optional[int] = None
    marketCap: Optional[float] = None
    fiftyTwoWeekHigh: Optional[float] = None
    fiftyTwoWeekLow: Optional[float] = None
    averageVolume: Optional[int] = None
    # Add more fields as needed from yfinance or other sources

class StockData(BaseModel):
    symbol: str
    info: Optional[StockTickerInfo] = None
    # For historical data, you might have a list of OHLCV points
    # history: Optional[List[Dict[str, Any]]] = None
    # Example for a single price point for simplicity now
    currentPrice: Optional[float] = None
    lastClose: Optional[float] = None
    # other relevant fields

class ForexData(BaseModel):
    pair: str # e.g., USDINR
    rate: float
    timestamp: Optional[int] = None

class CommodityData(BaseModel):
    name: str # e.g., GOLD, SILVER, CRUDE_OIL
    price: float
    unit: Optional[str] = None # e.g., USD per ounce
    currency: Optional[str] = None # e.g., USD
    timestamp: Optional[int] = None

class IndexData(BaseModel):
    symbol: str # e.g., ^NSEI for NIFTY 50
    name: Optional[str] = None
    currentPrice: Optional[float] = None
    previousClose: Optional[float] = None
    open: Optional[float] = None
    dayHigh: Optional[float] = None
    dayLow: Optional[float] = None
    # Add more fields as needed

class MarketNews(BaseModel):
    title: str
    link: str
    source: Optional[str] = None
    published_at: Optional[str] = None # Consider using datetime
    summary: Optional[str] = None # For AI summarized content

class MarketOverview(BaseModel):
    indices: List[IndexData]
    top_gainers: Optional[List[StockData]] = None # Simplified for now
    top_losers: Optional[List[StockData]] = None  # Simplified for now
    # market_news: Optional[List[MarketNews]] = None
    # key_commodities: Optional[List[CommodityData]] = None
    # key_forex_pairs: Optional[List[ForexData]] = None

# For historical chart data
class CandlestickDataPoint(BaseModel):
    timestamp: int # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None

class HistoricalDataResponse(BaseModel):
    symbol: str
    data: List[CandlestickDataPoint]
    timeframe: str # e.g., 1d, 1wk, 1mo
