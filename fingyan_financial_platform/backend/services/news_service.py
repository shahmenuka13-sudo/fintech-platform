import yfinance as yf
from typing import List, Optional
from datetime import datetime
import asyncio # For potential async operations later if needed

from ..models.news_models import NewsArticle

# For summarization (optional, placeholder for now)
# from transformers import pipeline # Example library

# summarizer = None
# def get_summarizer():
#     global summarizer
#     if summarizer is None:
#         try:
#             # Using a lightweight model for summarization
#             # This will download the model on first run, which can be slow.
#             # Consider pre-loading or using a dedicated microservice for this.
#             summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")
#             print("Summarization pipeline loaded.")
#         except Exception as e:
#             print(f"Failed to load summarization pipeline: {e}")
#             # summarizer will remain None, and summarization will be skipped
#     return summarizer

async def fetch_news_for_symbol(symbol: str, limit: int = 10) -> List[NewsArticle]:
    """
    Fetches news articles for a given stock symbol using yfinance.
    """
    articles_data: List[NewsArticle] = []
    try:
        ticker = yf.Ticker(symbol)
        # .news returns a list of dictionaries
        news_items = ticker.news

        if not news_items:
            return []

        for item in news_items[:limit]: # Apply limit
            # yfinance news item keys: 'uuid', 'title', 'publisher', 'link', 'providerPublishTime', 'type'
            # 'providerPublishTime' is a unix timestamp (seconds)

            publish_time = None
            if 'providerPublishTime' in item:
                try:
                    # Convert Unix timestamp to datetime
                    publish_time = datetime.fromtimestamp(item['providerPublishTime'])
                except Exception as e:
                    print(f"Error converting timestamp {item['providerPublishTime']} for '{item.get('title')}': {e}")
                    publish_time = None # Or datetime.now() or some other default

            article = NewsArticle(
                uuid=item.get('uuid'),
                title=item.get('title', 'No Title Provided'),
                link=item.get('link', 'about:blank'), # Provide a default valid URL
                publisher=item.get('publisher'),
                provider_publish_time=publish_time
                # type=item.get('type')
            )
            articles_data.append(article)

    except Exception as e:
        print(f"Error fetching news for {symbol} from yfinance: {e}")
        # Depending on policy, could raise an exception or return empty list
        # For now, return empty list on error to not break entire API call
        return []

    return articles_data

async def fetch_general_market_news(limit: int = 10) -> List[NewsArticle]:
    """
    Fetches general market news.
    yfinance does not have a direct general market news endpoint without a symbol.
    This function might need to use a list of broad market indices (e.g., NIFTY, SENSEX for India)
    or a different news provider entirely (e.g., NewsAPI, AlphaVantage with API keys).

    For now, as a placeholder, it could fetch news for a major index like NIFTY 50.
    """
    # Placeholder: Fetch news for a major Indian index like NIFTY 50 (^NSEI)
    # This is not truly "general" market news but a common proxy.
    print("Fetching general market news by using ^NSEI as a proxy with yfinance.")
    return await fetch_news_for_symbol("^NSEI", limit=limit)


# --- Placeholder for AI Summarization ---
async def summarize_text(text: str, max_length: int = 150, min_length: int = 30) -> Optional[str]:
    """
    Summarizes a given text using a pre-loaded Hugging Face pipeline.
    Returns None if summarizer is not available or summarization fails.
    This is a blocking operation if the pipeline is not run in a separate thread/process.
    For production, consider an async wrapper or a dedicated service.
    """
    # sum_pipeline = get_summarizer()
    # if not sum_pipeline:
    #     print("Summarizer not available. Skipping summarization.")
    #     return None

    # try:
    #     # For true async, this would need to run in a thread using asyncio.to_thread
    #     # summary = await asyncio.to_thread(sum_pipeline, text, max_length=max_length, min_length=min_length, do_sample=False)
    #     # For now, let's assume it's okay to be blocking for a moment or this is called from a worker.
    #     # summary_list = sum_pipeline(text, max_length=max_length, min_length=min_length, do_sample=False)
    #     # if summary_list and isinstance(summary_list, list) and 'summary_text' in summary_list[0]:
    #     #     return summary_list[0]['summary_text']
    #     print("AI Summarization is currently a placeholder and not active.")
    #     return f"Summary placeholder for: {text[:100]}..." # Placeholder
    # except Exception as e:
    #     print(f"Error during summarization: {e}")
    #     return None
    print("AI Summarization is currently a placeholder and not active.")
    return f"Summary placeholder for: {text[:100]}..." # Placeholder for now to avoid heavy deps / long setup

# Note: Using yfinance for news is convenient as it doesn't require API keys,
# but the quality and quantity of news might be limited.
# For production-grade news, dedicated APIs like NewsAPI.org, Alpha Vantage,
# Finnhub, or commercial providers are recommended. These usually require API keys
# and may have costs associated.

# The summarization part is also a heavy operation. In a real system:
# 1. It would run in a separate worker/process.
# 2. Models would be pre-loaded.
# 3. Consider using smaller/faster models if latency is critical or use a dedicated API.
# For now, the summarization call is commented out to avoid dependency and performance issues.
# It's marked as a future enhancement.
