import streamlit as st
import requests
import pandas as pd
from typing import Optional, Dict, List, Any

# Get API URL from Streamlit secrets or environment variable for flexibility
# Fallback to a default if not set (useful for local dev without secrets)
# In production on Streamlit Cloud, set this as a secret.
# In Docker, this would be an environment variable.
FASTAPI_BACKEND_URL = st.secrets.get("FASTAPI_BACKEND_URL", "http://backend:8000/api")
# For local dev where frontend runs directly on host and backend in Docker:
# FASTAPI_BACKEND_URL = "http://localhost:8000/api"

# --- Health Check ---
@st.cache_data(ttl=60) # Cache for 1 minute
def get_backend_health() -> Optional[Dict[str, Any]]:
    """Checks the health of the backend API."""
    try:
        # The health endpoint in backend main.py is at /health, not /api/health
        health_url = FASTAPI_BACKEND_URL.replace("/api", "") + "/health"
        response = requests.get(health_url, timeout=5)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Health Check failed: {e}")
        return None
    except Exception as e: # Catch any other unexpected errors
        print(f"An unexpected error occurred during health check: {e}")
        return None

# --- Market Data ---
@st.cache_data(ttl=60) # Cache for 1 minute
def get_index_data(index_symbol: str) -> Optional[Dict[str, Any]]:
    """Fetches data for a specific market index."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/market/index/{index_symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching index {index_symbol}: {e}")
        return None

@st.cache_data(ttl=60) # Cache for 1 minute
def get_stock_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetches current data for a stock symbol."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/market/stock/{symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching stock data for {symbol}: {e}")
        return None

@st.cache_data(ttl=300) # Cache for 5 minutes
def get_stock_historical_data(symbol: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetches historical stock data and returns a DataFrame."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/market/stock/{symbol}/history"
        params = {"period": period, "interval": interval}
        response = requests.get(url, params=params, timeout=20) # Longer timeout for history
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data.get("data", []))
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('timestamp')
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching historical data for {symbol}: {e}")
        return None
    except Exception as e:
        st.error(f"Error processing historical data for {symbol}: {e}")
        return None

# --- Portfolio Data ---
# TODO: Add functions for portfolio API calls, considering authentication headers if needed.
# These will require passing a user token once auth is implemented.

# --- Alerts Data ---
# TODO: Add functions for alerts API calls.

# --- News Data ---
@st.cache_data(ttl=15*60) # Cache for 15 minutes
def get_news_for_symbol(symbol: str, limit: int = 10, summarize: bool = False) -> Optional[List[Dict[str,Any]]]:
    try:
        url = f"{FASTAPI_BACKEND_URL}/news/symbol/{symbol}"
        params = {"limit": limit, "summarize": summarize}
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json().get("articles", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching news for {symbol}: {e}")
        return None

@st.cache_data(ttl=15*60) # Cache for 15 minutes
def get_market_news(limit: int = 10, summarize: bool = False) -> Optional[List[Dict[str,Any]]]:
    try:
        url = f"{FASTAPI_BACKEND_URL}/news/market"
        params = {"limit": limit, "summarize": summarize}
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json().get("articles", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching market news: {e}")
        return None

# --- Predictions ---
# TODO: Add functions for prediction API calls.

# --- Portfolio Management ---
# For now, these assume a DUMMY_USER_ID is handled by the backend if no auth token is passed.
# Once auth is implemented, a token would be included in headers.

@st.cache_data(ttl=10) # Short TTL for portfolio data as it can change frequently
def get_portfolios() -> Optional[List[Dict[str, Any]]]:
    """Fetches all portfolios for the (dummy) user."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching portfolios: {e}")
        return None

@st.cache_data(ttl=10)
def get_portfolio_details(portfolio_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific portfolio."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/{portfolio_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching portfolio {portfolio_id}: {e}")
        return None

def create_portfolio(name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Creates a new portfolio."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/"
        payload = {"name": name, "description": description}
        # Filter out None description for cleaner payload
        payload = {k: v for k, v in payload.items() if v is not None}
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        # Clear cache for get_portfolios after creating a new one
        st.cache_data.clear() # Clears all @st.cache_data, fine for now.
                              # For more granular control, would need specific cache key invalidation if Streamlit supports it easily.
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating portfolio '{name}': {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return None

def update_portfolio(portfolio_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates an existing portfolio."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/{portfolio_id}"
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        if not payload:
            st.warning("No changes provided for portfolio update.")
            return get_portfolio_details(portfolio_id) # Return current details

        response = requests.put(url, json=payload, timeout=10)
        response.raise_for_status()
        st.cache_data.clear() # Clear relevant caches
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating portfolio {portfolio_id}: {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return None

def delete_portfolio(portfolio_id: int) -> bool:
    """Deletes a portfolio."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/{portfolio_id}"
        response = requests.delete(url, timeout=10)
        response.raise_for_status() # Should be 204 No Content on success
        st.cache_data.clear() # Clear relevant caches
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting portfolio {portfolio_id}: {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return False

def add_or_update_holding(portfolio_id: int, symbol: str, quantity: float, average_buy_price: float) -> Optional[Dict[str, Any]]:
    """Adds or updates a holding in a portfolio."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/{portfolio_id}/holdings"
        payload = {
            "symbol": symbol.upper(),
            "quantity": quantity,
            "average_buy_price": average_buy_price
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        st.cache_data.clear() # Clear relevant caches (specifically get_portfolio_details)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error adding/updating holding '{symbol}' to portfolio {portfolio_id}: {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return None

def remove_holding(portfolio_id: int, symbol: str) -> bool:
    """Removes a holding from a portfolio."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/portfolio/{portfolio_id}/holdings/{symbol.upper()}"
        response = requests.delete(url, timeout=10)
        response.raise_for_status() # Should be 204 No Content
        st.cache_data.clear() # Clear relevant caches
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error removing holding '{symbol}' from portfolio {portfolio_id}: {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return False

# --- Alerts Management ---
@st.cache_data(ttl=15) # Cache alerts for a short duration
def get_alerts(symbol: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[List[Dict[str, Any]]]:
    """Fetches alerts for the (dummy) user, with optional filters."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/alerts/"
        params = {}
        if symbol:
            params["symbol"] = symbol
        if is_active is not None:
            params["is_active"] = is_active

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching alerts: {e}")
        return None

def create_alert(
    symbol: str,
    alert_type: str, # "price" for now
    target_price: Optional[float] = None,
    trigger_when_above: Optional[bool] = None,
    description: Optional[str] = None,
    is_active: bool = True
) -> Optional[Dict[str, Any]]:
    """Creates a new alert."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/alerts/"
        payload = {
            "symbol": symbol.upper(),
            "alert_type": alert_type,
            "target_price": target_price,
            "trigger_when_above": trigger_when_above,
            "description": description,
            "is_active": is_active
        }
        # Filter out None values for optional fields to avoid issues with Pydantic server-side if not explicitly Optional there
        payload = {k: v for k, v in payload.items() if v is not None or k in ["symbol", "alert_type", "is_active"]}


        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        get_alerts.clear() # Clear cache for alerts list
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating alert for '{symbol}': {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return None

def update_alert(
    alert_id: int,
    target_price: Optional[float] = None,
    trigger_when_above: Optional[bool] = None,
    is_active: Optional[bool] = None,
    description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Updates an existing alert."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/alerts/{alert_id}"
        payload = {}
        if target_price is not None: payload["target_price"] = target_price
        if trigger_when_above is not None: payload["trigger_when_above"] = trigger_when_above
        if is_active is not None: payload["is_active"] = is_active
        if description is not None: payload["description"] = description

        if not payload:
            st.warning("No changes provided for alert update.")
            # To get current details, another function would be needed or get_alerts could be filtered.
            # For now, just return None if no payload.
            return None

        response = requests.put(url, json=payload, timeout=10)
        response.raise_for_status()
        get_alerts.clear() # Clear alerts cache
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating alert {alert_id}: {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return None

def delete_alert(alert_id: int) -> bool:
    """Deletes an alert."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/alerts/{alert_id}"
        response = requests.delete(url, timeout=10)
        response.raise_for_status() # Should be 204 No Content
        get_alerts.clear() # Clear alerts cache
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting alert {alert_id}: {e}")
        if e.response is not None:
             st.error(f"Backend response: {e.response.text}")
        return False

# --- Predictions ---
@st.cache_data(ttl=5*60) # Cache predictions for 5 minutes
def get_trend_prediction(symbol: str, horizon_days: int = 7) -> Optional[Dict[str, Any]]:
    """Fetches a trend prediction for a given symbol and horizon."""
    try:
        url = f"{FASTAPI_BACKEND_URL}/predict/trend"
        payload = {
            "symbol": symbol.upper(),
            "prediction_horizon_days": horizon_days
        }
        response = requests.post(url, json=payload, timeout=20) # Longer timeout for potential model inference
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching prediction for '{symbol}': {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", e.response.text)
            except ValueError: # Not JSON
                error_detail = e.response.text
            st.error(f"Backend response: {error_detail}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching prediction: {e}")
        return None


# Note on Error Handling:
# These functions currently use st.error() to display errors directly on the Streamlit page.
# For more complex applications, you might want a more centralized error handling strategy
# or allow pages to handle errors from API calls more gracefully.
# Returning None allows the calling page to check and display custom messages or fallbacks.

# Note on FASTAPI_BACKEND_URL:
# If running Streamlit frontend locally (e.g. `streamlit run frontend/app.py`) and
# the FastAPI backend is running in Docker via `docker-compose up backend`,
# then the URL should be `http://localhost:8000/api` because `localhost` from the
# Streamlit app's perspective (running on your host machine) correctly points to the
# Docker-exposed port.
# If both frontend and backend are run via `docker-compose up`, then `http://backend:8000/api`
# is correct because they are on the same Docker network.
# The st.secrets approach is good for Streamlit Cloud deployment.
# For local, you might need to manually set it or use a .env file loaded by Streamlit (less common).
# The current default "http://backend:8000/api" assumes docker-compose context for both.
# I will add a small note in app.py for this or rely on st.secrets.
# For now, I'll assume the st.secrets method or the default "http://backend:8000/api" is fine.
