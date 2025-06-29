from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from redis.asyncio import Redis as AsyncRedis # For caching
import json

from ..services import news_service
from ..models.news_models import NewsResponse, NewsArticle
from .market_router import get_redis_client # Re-use redis dependency

router = APIRouter()

@router.get("/symbol/{symbol}", response_model=NewsResponse)
async def get_news_for_symbol(
    symbol: str,
    limit: int = Query(10, ge=1, le=50), # Max 50 articles
    summarize: bool = Query(False, description="Enable AI summarization for articles (placeholder)."),
    redis: AsyncRedis = Depends(get_redis_client)
):
    """
    Get news articles for a specific stock symbol.
    Results are cached for 15 minutes.
    yfinance service returns an empty list if symbol is invalid or no news is found.
    """
    cache_key = f"news_symbol:{symbol}:{limit}:{summarize}"
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            # Pydantic will validate on return
            return NewsResponse(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis GET error for news {cache_key}: {e}")

    articles = await news_service.fetch_news_for_symbol(symbol, limit=limit)
    # `fetch_news_for_symbol` returns empty list on error or no news.
    # If articles list is empty, client can decide how to interpret (e.g. "No news found for {symbol}").
    # No explicit 404 here unless we want to differentiate bad symbol vs no news,
    # which would require more detailed error from service.

    if summarize:
        # Placeholder for summarization call for each article
        # This would be slow if done serially here. Ideal for background processing or optimized service.
        print(f"Summarization requested for {len(articles)} articles (currently a placeholder).")
        for article in articles:
            if article.link: # Assuming we might summarize content from link, or if abstract is available
                article.summary = await news_service.summarize_text(f"{article.title} Link: {article.link}")

    response = NewsResponse(symbol=symbol, articles=articles, source_info="yfinance")

    try:
        await redis.set(cache_key, response.model_dump_json(), ex=15*60) # Cache for 15 minutes
    except Exception as e:
        print(f"Redis SET error for news {cache_key}: {e}")

    return response

@router.get("/market", response_model=NewsResponse)
async def get_general_market_news(
    limit: int = Query(10, ge=1, le=50),
    summarize: bool = Query(False, description="Enable AI summarization for articles (placeholder)."),
    redis: AsyncRedis = Depends(get_redis_client)
):
    """
    Get general market news (currently uses NIFTY news as a proxy via yfinance).
    Results are cached for 15 minutes.
    """
    cache_key = f"news_market:{limit}:{summarize}"
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return NewsResponse(**json.loads(cached_data))
    except Exception as e:
        print(f"Redis GET error for market news {cache_key}: {e}")

    articles = await news_service.fetch_general_market_news(limit=limit)

    if summarize:
        print(f"Summarization requested for {len(articles)} general market articles (currently a placeholder).")
        for article in articles:
            if article.link:
                article.summary = await news_service.summarize_text(f"{article.title} Link: {article.link}")

    response = NewsResponse(articles=articles, source_info="yfinance (using ^NSEI as proxy)")

    try:
        await redis.set(cache_key, response.model_dump_json(), ex=15*60) # Cache for 15 minutes
    except Exception as e:
        print(f"Redis SET error for market news {cache_key}: {e}")

    return response


# TODO:
# - Implement actual AI summarization (currently placeholder). This should ideally be
#   done asynchronously or by a separate worker to avoid blocking API responses.
# - Consider more robust news sources than yfinance for production (e.g. NewsAPI, Finnhub).
# - Add error handling for yfinance calls within the service using Tenacity.
# - The current summarization is a placeholder and would block if implemented naively.
#   A proper implementation would use `asyncio.to_thread` for the Hugging Face pipeline
#   or call a dedicated microservice.
# - `providerPublishTime` in yfinance news is a Unix timestamp; ensure it's correctly
#   handled and converted to ISO datetime string or similar for JSON response if not already.
#   (Handled in news_service.py by converting to datetime object, Pydantic handles serialization).
