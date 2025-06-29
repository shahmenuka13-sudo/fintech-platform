import json
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
import yfinance as yf
from redis.asyncio import Redis as AsyncRedis
import pandas as pd
import asyncio # For asyncio.to_thread
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..models.market_models import (
    StockData, StockTickerInfo, ForexData, CommodityData, IndexData,
    HistoricalDataResponse, CandlestickDataPoint
)
# from ..services.market_data_service import fetch_stock_data_from_source, ...
# For now, direct yfinance calls. Will refactor to services later.


router = APIRouter()

# Dependency to get Redis client from request state
async def get_redis_client(request: Request) -> AsyncRedis:
    return request.app.state.redis

# Helper function to get data from yfinance Ticker object
# This function is synchronous and will be wrapped with asyncio.to_thread
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((IOError, TimeoutError)) # Example: retry on network-related issues
    # More specific yfinance exceptions could be added if they are common and retryable
)
def fetch_yfinance_ticker_info_sync(symbol: str) -> dict:
    """Synchronous helper to fetch ticker.info from yfinance."""
    # print(f"Attempting to fetch yfinance info for {symbol} (sync)")
    ticker = yf.Ticker(symbol)
    info = ticker.info # This is the blocking call
    if not info or info.get('regularMarketPrice') is None : # Check if info is empty or lacks a key price field
        # yfinance sometimes returns minimal info for invalid tickers or when data is missing.
        # Or if market is closed, some fields might be None.
        # Consider what constitutes a "valid" info response.
        # For some symbols, info might be sparse. If 'regularMarketPrice' is missing, it might be an issue.
        # This check helps tenacity to retry if a bad/empty response is received.
        # A more robust check would depend on which fields are absolutely essential.
        # If info is consistently bad for a valid symbol, this might cause excessive retries.
        # A better approach for "bad/empty data" might be specific checks rather than raising IOError.
        # For now, let's assume if 'regularMarketPrice' is missing, data is incomplete.
        # This is a simple heuristic.
        # print(f"Incomplete info received for {symbol}, yfinance might return minimal dict on errors.")
        if not info.get('regularMarketPrice') and not info.get('previousClose'): # If critical price data missing
             raise IOError(f"Incomplete or missing critical data in yfinance info for {symbol}")
    return info

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((IOError, TimeoutError))
)
def fetch_yfinance_history_sync(symbol: str, period: str = "2d", interval: str = "1d") -> pd.DataFrame:
    """Synchronous helper to fetch ticker.history from yfinance."""
    # print(f"Attempting to fetch yfinance history for {symbol} (sync)")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period, interval=interval) # Blocking call
    if hist.empty:
        # Similar to info, if history is empty, it might be an issue with the symbol or data source.
        # Raising an error here can allow tenacity to retry.
        # However, an empty history for a very short period or new stock could be valid.
        # For broader periods like "1y", empty usually means an issue.
        # Let's only raise for "significant" periods if empty, or always if that's the policy.
        # For now, let's assume empty history is a retryable issue.
        raise IOError(f"Empty history received from yfinance for {symbol} with period {period}")
    return hist


def process_ticker_info_data(info: dict, symbol: str) -> StockTickerInfo:
    """Processes the dictionary from yfinance info into StockTickerInfo Pydantic model."""
    return StockTickerInfo(
        symbol=symbol, # Use the original requested symbol for consistency
        shortName=info.get('shortName'),
        longName=info.get('longName'),
        currency=info.get('currency'),
        exchange=info.get('exchange'),
        market=info.get('market'),
        previousClose=info.get('previousClose'),
        open=info.get('open'),
        dayHigh=info.get('dayHigh'),
        dayLow=info.get('dayLow'),
        volume=info.get('volume'),
        marketCap=info.get('marketCap'),
        fiftyTwoWeekHigh=info.get('fiftyTwoWeekHigh'),
        fiftyTwoWeekLow=info.get('fiftyTwoWeekLow'),
        averageVolume=info.get('averageVolume')
    )

@router.get("/stock/{symbol}", response_model=StockData)
async def get_stock_data(
    symbol: str,
    request: Request, # Used for accessing app state like redis
    redis: AsyncRedis = Depends(get_redis_client) # Dependency injection for Redis
):
    """
    Get current market data for a given stock symbol (e.g., RELIANCE.NS, AAPL).
    Uses yfinance as the data source.
    Caches results in Redis for 60 seconds.
    """
    cache_key = f"stock_data:{symbol}"
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return StockData(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis GET error for {cache_key}: {e}") # Log error and proceed to fetch

    try:
        # Run synchronous yfinance calls in a separate thread
        # info_dict = await asyncio.to_thread(fetch_yfinance_ticker_info_sync, symbol)
        # hist_df = await asyncio.to_thread(fetch_yfinance_history_sync, symbol, period="2d", interval="1d")

        # Using a gather to run them pseudo-concurrently if they are independent I/O
        results = await asyncio.gather(
            asyncio.to_thread(fetch_yfinance_ticker_info_sync, symbol),
            asyncio.to_thread(fetch_yfinance_history_sync, symbol, period="2d", interval="1d"),
            return_exceptions=True # Allows to catch individual errors if needed
        )

        # Process results, checking for errors from gather
        info_dict_result, hist_df_result = results

        if isinstance(info_dict_result, Exception):
            print(f"Error fetching yfinance info for {symbol} after retries: {info_dict_result}")
            raise HTTPException(status_code=503, detail=f"Could not fetch ticker info for {symbol} from data provider: {str(info_dict_result)}")

        if isinstance(hist_df_result, Exception):
            print(f"Error fetching yfinance history for {symbol} after retries: {hist_df_result}")
            # Depending on strictness, you might still proceed with info_dict if hist fails, or fail all
            raise HTTPException(status_code=503, detail=f"Could not fetch ticker history for {symbol} from data provider: {str(hist_df_result)}")

        info_data = process_ticker_info_data(info_dict_result, symbol)

        current_price = None
        last_close = None
        if not hist_df_result.empty:
            current_price = hist_df_result['Close'].iloc[-1]
            if len(hist_df_result) > 1:
                last_close = hist_df_result['Close'].iloc[-2]
            else:
                last_close = info_data.open if info_data.open else info_data.previousClose
        else: # Fallback if history is empty (should have been caught by retry logic in fetch_yfinance_history_sync)
            print(f"Warning: History was empty for {symbol} even after potential retries. Using info for prices.")
            current_price = info_data.dayHigh # Or some other field from info as a fallback
            last_close = info_data.previousClose


        stock_data_obj = StockData(
            symbol=symbol,
            info=info_data,
            currentPrice=current_price,
            lastClose=last_close
        )

        try:
            await redis.set(cache_key, stock_data_obj.model_dump_json(), ex=60) # Cache for 60 seconds
        except Exception as e:
            print(f"Redis SET error for {cache_key}: {e}")

        return stock_data_obj
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        # Catch other unexpected errors (e.g. from gather, processing)
        print(f"Unexpected error processing stock data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error processing data for {symbol}: {str(e)}")


@router.get("/stock/{symbol}/history", response_model=HistoricalDataResponse)
async def get_stock_historical_data(
    symbol: str,
    period: str = "1y", # e.g., 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max
    interval: str = "1d", # e.g., 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    redis: AsyncRedis = Depends(get_redis_client)
):
    """
    Get historical OHLCV data for a given stock symbol.
    Caches results in Redis for 300 seconds (5 minutes).
    """
    cache_key = f"stock_history:{symbol}:{period}:{interval}"
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            # Pydantic validation happens implicitly when returning HistoricalDataResponse
            return HistoricalDataResponse(**data)
    except Exception as e:
        print(f"Redis GET error for {cache_key}: {e}")

    try:
        ticker = yf.Ticker(symbol)
        hist_df = ticker.history(period=period, interval=interval)

        if hist_df.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol} with period={period} and interval={interval}")

        candlestick_data = []
        for index, row in hist_df.iterrows():
            candlestick_data.append(
                CandlestickDataPoint(
                    timestamp=int(index.timestamp()), # Convert pandas Timestamp to unix timestamp
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row.get('Volume') # Volume might not always be present
                )
            )

        response_data = HistoricalDataResponse(
            symbol=symbol,
            data=candlestick_data,
            timeframe=f"{period}_{interval}" # Or just pass interval
        )

        try:
            await redis.set(cache_key, response_data.model_dump_json(), ex=300) # Cache for 5 minutes
        except Exception as e:
            print(f"Redis SET error for {cache_key}: {e}")

        return response_data
    except Exception as e:
        print(f"yfinance history error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not fetch historical data for {symbol}: {str(e)}")


@router.get("/index/{index_symbol}", response_model=IndexData)
async def get_index_data(
    index_symbol: str, # e.g., ^NSEI for NIFTY, ^BSESN for SENSEX
    redis: AsyncRedis = Depends(get_redis_client)
):
    """
    Get current data for a major market index (e.g., ^NSEI, ^BSESN).
    Caches results in Redis for 60 seconds.
    """
    # yfinance uses specific symbols for indices, e.g., ^NSEI for NIFTY 50
    # We can create a mapping or expect users to know these.
    # For simplicity, direct symbol usage for now.
    cache_key = f"index_data:{index_symbol}"
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return IndexData(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis GET error for {cache_key}: {e}")

    try:
        ticker = yf.Ticker(index_symbol)
        info = ticker.info

        # For indices, 'currentPrice' might not be in info. Use history for latest price.
        hist = ticker.history(period="2d", interval="1d") # Short period to get latest close
        current_price = None
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]

        index_data_obj = IndexData(
            symbol=index_symbol,
            name=info.get('shortName', info.get('longName')),
            currentPrice=current_price if current_price is not None else info.get('regularMarketPrice'), # Fallback
            previousClose=info.get('previousClose'),
            open=info.get('open'),
            dayHigh=info.get('dayHigh'),
            dayLow=info.get('dayLow')
        )

        try:
            await redis.set(cache_key, index_data_obj.model_dump_json(), ex=60)
        except Exception as e:
            print(f"Redis SET error for {cache_key}: {e}")

        return index_data_obj
    except Exception as e:
        print(f"yfinance error for index {index_symbol}: {e}")
        raise HTTPException(status_code=404, detail=f"Data not found for index {index_symbol}: {str(e)}")

# TODO:
# - /forex/{pair} (e.g., /forex/USDINR)
# - /commodity/{name} (e.g., /commodity/GOLD)
# - /market/overview (NIFTY, SENSEX, Top Gainers/Losers - this might need more complex logic or another data source)
# - Error handling and resilience (e.g., using Tenacity for retries on yfinance calls if appropriate)
# - Consider a background task to pre-fetch popular symbols or warm the cache.
# - Standardize yfinance symbols (e.g. always use .NS for NSE stocks if applicable)
# - API Key management if switching to paid data sources.
# - More robust parsing of yf.Ticker.info as fields can be missing.
# - For forex, yfinance format is "USDINR=X"
# - For commodities, yfinance symbols like "GC=F" for Gold, "SI=F" for Silver, "CL=F" for Crude Oil.

# Example for Forex
@router.get("/forex/{base_currency}-{quote_currency}", response_model=ForexData)
async def get_forex_rate(
    base_currency: str,
    quote_currency: str,
    redis: AsyncRedis = Depends(get_redis_client)
):
    """
    Get current exchange rate for a currency pair (e.g., USD-INR).
    Uses yfinance. Caches for 5 minutes.
    """
    pair_symbol = f"{base_currency.upper()}{quote_currency.upper()}=X"
    cache_key = f"forex_data:{pair_symbol}"

    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return ForexData(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis GET error for {cache_key}: {e}")

    try:
        ticker = yf.Ticker(pair_symbol)
        # For currency pairs, 'regularMarketPrice' or 'previousClose' is often the rate
        info = ticker.info
        rate = info.get('regularMarketPrice', info.get('previousClose'))

        if rate is None:
            # Fallback to history if direct info is not available
            hist = ticker.history(period="2d")
            if not hist.empty:
                rate = hist['Close'].iloc[-1]
            else:
                raise HTTPException(status_code=404, detail=f"Could not find rate for forex pair {pair_symbol}")

        forex_data_obj = ForexData(
            pair=f"{base_currency.upper()}{quote_currency.upper()}",
            rate=rate,
            # timestamp = info.get('regularMarketTime') # yfinance provides this
        )

        try:
            await redis.set(cache_key, forex_data_obj.model_dump_json(), ex=300) # Cache for 5 minutes
        except Exception as e:
            print(f"Redis SET error for {cache_key}: {e}")

        return forex_data_obj
    except Exception as e:
        print(f"yfinance error for forex pair {pair_symbol}: {e}")
        raise HTTPException(status_code=404, detail=f"Data not found for forex pair {pair_symbol}: {str(e)}")

# Example for Commodity
@router.get("/commodity/{commodity_symbol}", response_model=CommodityData)
async def get_commodity_price(
    commodity_symbol: str, # e.g., GC=F (Gold), SI=F (Silver), CL=F (Crude Oil)
    redis: AsyncRedis = Depends(get_redis_client)
):
    """
    Get current price for a commodity (e.g., GC=F for Gold).
    Uses yfinance. Caches for 5 minutes.
    Provide yfinance compatible symbols like GC=F, SI=F, CL=F.
    """
    cache_key = f"commodity_data:{commodity_symbol}"
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return CommodityData(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis GET error for {cache_key}: {e}")

    try:
        ticker = yf.Ticker(commodity_symbol)
        info = ticker.info
        price = info.get('regularMarketPrice', info.get('previousClose'))

        if price is None:
            hist = ticker.history(period="2d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                raise HTTPException(status_code=404, detail=f"Could not find price for commodity {commodity_symbol}")

        commodity_data_obj = CommodityData(
            name=info.get('shortName', commodity_symbol), # yfinance shortName is good here
            price=price,
            unit=info.get('quoteType'), # This might give 'FUTURE' etc. May need manual mapping for units.
            currency=info.get('currency')
            # timestamp = info.get('regularMarketTime')
        )

        try:
            await redis.set(cache_key, commodity_data_obj.model_dump_json(), ex=300) # Cache for 5 minutes
        except Exception as e:
            print(f"Redis SET error for {cache_key}: {e}")

        return commodity_data_obj
    except Exception as e:
        print(f"yfinance error for commodity {commodity_symbol}: {e}")
        raise HTTPException(status_code=404, detail=f"Data not found for commodity {commodity_symbol}: {str(e)}")
