from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock # For mocking async functions and yfinance
import pytest
import pandas as pd
from datetime import datetime

from backend.main import app # Main FastAPI app
# from backend.services.market_data_service import ... # If we had a separate service layer
# from backend.api.market_router import get_redis_client # To mock redis if needed for specific tests

client = TestClient(app)

# --- Mocking yfinance ---
# We need to mock yfinance.Ticker and its methods (.info, .history)
# as these make external network calls.

# Sample yfinance data
SAMPLE_TICKER_INFO = {
    'shortName': 'Reliance Industries', 'longName': 'Reliance Industries Limited',
    'currency': 'INR', 'exchange': 'NSI', 'market': 'in_market',
    'previousClose': 2800.0, 'open': 2810.0, 'dayHigh': 2850.0, 'dayLow': 2805.0,
    'volume': 5000000, 'marketCap': 20000000000000,
    'fiftyTwoWeekHigh': 3000.0, 'fiftyTwoWeekLow': 2000.0, 'averageVolume': 4500000,
    'regularMarketPrice': 2830.0 # Added for some internal yf logic checks
}

SAMPLE_HISTORY_DATA = pd.DataFrame({
    'Open': [2810.0, 2820.0], 'High': [2850.0, 2860.0],
    'Low': [2805.0, 2815.0], 'Close': [2830.0, 2855.0],
    'Volume': [5000000, 5100000]
}, index=pd.to_datetime([datetime.now() - pd.Timedelta(days=1), datetime.now()]))


@pytest.fixture
def mock_yfinance_ticker():
    """Mocks yfinance.Ticker calls."""
    with patch('yfinance.Ticker') as mock_ticker_class:
        mock_instance = mock_ticker_class.return_value
        # Configure what mock_instance.info and mock_instance.history return
        mock_instance.info = SAMPLE_TICKER_INFO
        mock_instance.history.return_value = SAMPLE_HISTORY_DATA
        yield mock_ticker_class # Yield the class mock to check calls if needed

@pytest.fixture
def mock_yfinance_empty_history():
    """Mocks yfinance.Ticker to return empty history."""
    with patch('yfinance.Ticker') as mock_ticker_class:
        mock_instance = mock_ticker_class.return_value
        mock_instance.info = SAMPLE_TICKER_INFO
        mock_instance.history.return_value = pd.DataFrame() # Empty DataFrame
        yield mock_ticker_class

@pytest.fixture
def mock_yfinance_incomplete_info():
    """Mocks yfinance.Ticker to return incomplete info (missing regularMarketPrice)."""
    with patch('yfinance.Ticker') as mock_ticker_class:
        mock_instance = mock_ticker_class.return_value
        incomplete_info = SAMPLE_TICKER_INFO.copy()
        del incomplete_info['regularMarketPrice'] # Simulate missing critical field
        mock_instance.info = incomplete_info
        mock_instance.history.return_value = SAMPLE_HISTORY_DATA
        yield mock_ticker_class

# --- Mocking Redis ---
# We also need to mock Redis calls if we are testing caching logic explicitly
# or if Redis connection failure affects the endpoint.
# The app's lifespan manager attempts to connect to Redis.
# TestClient runs lifespan events. If Redis isn't available, health check shows it.
# For market router, it tries to use Redis but falls back to fetching if Redis fails.

@pytest.fixture
async def mock_redis_client():
    """Mocks the Redis client used by the app state."""
    # This fixture can be used to override the app.state.redis
    # For more complex scenarios, you might patch where `aioredis.from_url` is called.
    # For simplicity here, we'll patch the direct yfinance calls and assume Redis might fail gracefully.
    # A more thorough test would involve testing with mock Redis available and unavailable.

    # Let's create a mock that simulates Redis get/set behavior for specific tests
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None # Default: cache miss
    mock_redis.set.return_value = True # Assume set succeeds
    mock_redis.ping.return_value = True # Assume ping succeeds for health check

    # To use this: client.app.state.redis = mock_redis before a test call
    # However, lifespan sets app.state.redis. We need to patch it more effectively.
    # For now, let's focus on mocking yfinance and assume Redis interaction is secondary
    # or tested by observing cache behavior (e.g., faster second call - harder in unit tests).

    # A simpler way for these tests is to let Redis calls fail (as they would if Redis isn't running)
    # and ensure the API still behaves correctly by fetching from yfinance.
    # The current API code has try-except around Redis calls.
    pass


# --- Tests for /api/market/stock/{symbol} ---

@pytest.fixture
def mock_redis_dependency_override(monkeypatch): # Added monkeypatch fixture
    """Fixture to override the get_redis_client dependency with a more controllable mock."""
    from backend.api.market_router import get_redis_client as actual_get_redis_client

    # Using a simple dictionary to simulate Redis storage for this mock
    mock_redis_storage = {}

    async def fake_redis_get(key):
        # print(f"DEBUG: FAKE REDIS GET for key: {key}, returning: {mock_redis_storage.get(key)}")
        return mock_redis_storage.get(key)

    async def fake_redis_set(key, value, ex=None):
        # print(f"DEBUG: FAKE REDIS SET for key: {key}, value: {str(value)[:100]}...")
        mock_redis_storage[key] = value
        return True

    mock_redis_object = AsyncMock()
    # Point methods to our fake async functions
    mock_redis_object.get = AsyncMock(side_effect=fake_redis_get)
    mock_redis_object.set = AsyncMock(side_effect=fake_redis_set)
    mock_redis_object.ping = AsyncMock(return_value=True) # For health checks if any test triggers it

    # Store original dependency if it exists, to restore later
    original_get_redis_client = app.dependency_overrides.get(actual_get_redis_client)

    app.dependency_overrides[actual_get_redis_client] = lambda: mock_redis_object

    yield mock_redis_object, mock_redis_storage # Yield both mock object and its storage for test manipulation

    # Teardown: clear the override and the storage
    if original_get_redis_client:
        app.dependency_overrides[actual_get_redis_client] = original_get_redis_client
    else:
        del app.dependency_overrides[actual_get_redis_client]
    mock_redis_storage.clear()


def test_get_stock_data_success(mock_yfinance_ticker, mock_redis_dependency_override):
    """Test successful retrieval of stock data."""
    # mock_redis_dependency_override fixture handles Redis mocking. It returns (mock_redis_object, mock_redis_storage)
    mock_redis_object, _ = mock_redis_dependency_override # We only need the object here, not storage

    symbol = "RELIANCE.NS"
    response = client.get(f"/api/market/stock/{symbol}")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["info"]["shortName"] == SAMPLE_TICKER_INFO["shortName"]
    assert data["currentPrice"] is not None # Based on SAMPLE_HISTORY_DATA
    assert data["lastClose"] is not None   # Based on SAMPLE_HISTORY_DATA

    # Check if yfinance.Ticker was called with the correct symbol
    mock_yfinance_ticker.assert_called_with(symbol)

    # Further checks can be added for specific values if needed

def test_get_stock_data_yfinance_info_fails(mock_yfinance_incomplete_info, mock_redis_dependency_override):
    """Test when yfinance.Ticker(...).info call fails or returns unexpected structure."""
    mock_redis_object, _ = mock_redis_dependency_override # Unpack, though not directly used for assertions on redis obj here
    symbol = "FAIL.NS"
    # mock_yfinance_incomplete_info now handles the yfinance side of failure for info.
    # We need to patch the sync helpers that are called by the router.
    # The fixture mock_yfinance_incomplete_info already patches yfinance.Ticker.
    # The router calls fetch_yfinance_ticker_info_sync and fetch_yfinance_history_sync.
    # These sync helpers internally call yfinance.Ticker.

    # Scenario 1: Info fetch fails (e.g. raises IOError from sync helper due to bad data)
    with patch('backend.api.market_router.fetch_yfinance_ticker_info_sync', side_effect=IOError("Simulated yfinance info error")):
        with patch('backend.api.market_router.fetch_yfinance_history_sync', return_value=SAMPLE_HISTORY_DATA):
            response = client.get(f"/api/market/stock/{symbol}")
            assert response.status_code == 503
            assert "Could not fetch ticker info" in response.json()["detail"]

    # Scenario 2: History fetch fails
    with patch('backend.api.market_router.fetch_yfinance_ticker_info_sync', return_value=SAMPLE_TICKER_INFO): # Info is fine
        with patch('backend.api.market_router.fetch_yfinance_history_sync', side_effect=IOError("Simulated yfinance history error")):
            response = client.get(f"/api/market/stock/{symbol}")
            assert response.status_code == 503
            assert "Could not fetch ticker history" in response.json()["detail"]


def test_get_stock_data_caching_behavior(mock_yfinance_ticker, mock_redis_dependency_override):
    """
    Test caching. First call fetches from yfinance, subsequent (within TTL) should be faster (mocked).
    This requires controlling the Redis mock more effectively.
    For now, this test will be conceptual as direct cache testing is complex without full Redis mock injection
    into app state for TestClient.
    A simple test: ensure yfinance is called once if Redis is "working" and data cached.
    """
    symbol = "INFY.NS"
    mock_redis_object, mock_redis_storage = mock_redis_dependency_override

    # Ensure cache is empty for the first call (it is by default with the new fixture)
    # mock_redis_object.get.side_effect will use fake_redis_get which reads from empty mock_redis_storage

    with patch('backend.api.market_router.fetch_yfinance_ticker_info_sync', return_value=SAMPLE_TICKER_INFO) as mock_fetch_info, \
         patch('backend.api.market_router.fetch_yfinance_history_sync', return_value=SAMPLE_HISTORY_DATA) as mock_fetch_hist:

        # First call - should hit yfinance mocks
        response1 = client.get(f"/api/market/stock/{symbol}")
        assert response1.status_code == 200
        mock_fetch_info.assert_called_once_with(symbol)
        mock_fetch_hist.assert_called_once_with(symbol, period="2d", interval="1d")
        mock_redis_object.get.assert_called_once() # Check Redis get was called
        mock_redis_object.set.assert_called_once() # Check Redis set was called

        # Simulate cache hit for a second call
        # The fake_redis_set in the fixture stored the value in mock_redis_storage.
        # The fake_redis_get will now retrieve it.

        mock_fetch_info.reset_mock()
        mock_fetch_hist.reset_mock()
        # mock_redis_object.get.reset_mock() # No, we want to see it called again
        mock_redis_object.set.reset_mock() # Set should not be called again on cache hit

        response2 = client.get(f"/api/market/stock/{symbol}")
        assert response2.status_code == 200
        assert response2.json() == response1.json()

        # Yfinance helpers should NOT have been called again due to cache hit
        mock_fetch_info.assert_not_called()
        mock_fetch_hist.assert_not_called()
        # mock_redis_instance.set.assert_called_once() # Should still be called once from the first request


# --- Tests for /api/market/stock/{symbol}/history ---
# def test_get_stock_historical_data_success(mock_redis_dependency_override): # Removed mock_yfinance_ticker
#     symbol = "TCS.NS"
#     period = "1mo"
#     interval = "1d"

#     # Define sample history data locally for this test to avoid global state issues
#     local_sample_history_data = pd.DataFrame({
#         'Open': [2810.0, 2820.0], 'High': [2850.0, 2860.0],
#         'Low': [2805.0, 2815.0], 'Close': [2830.0, 2855.0],
#         'Volume': [5000000, 5100000]
#     }, index=pd.to_datetime([datetime(2023,1,1), datetime(2023,1,2)])) # Use fixed dates

#     # mock_redis_dependency_override handles Redis
#     mock_redis_object, _ = mock_redis_dependency_override # Unpack the tuple
#     mock_redis_object.get.return_value = None # Cache miss for this test run
#     mock_redis_object.set = AsyncMock(return_value=True) # Ensure set is an awaitable mock

#     # Using pytest.monkeypatch to replace the function
#     from backend.api import market_router # Import the module where the function lives

#     class MyCustomTestException(Exception): pass

#     def mock_fetch_sync_side_effect(*args, **kwargs):
#         # This function will replace fetch_yfinance_history_sync
#         # We can assert it was called and then raise the exception
#         mock_fetch_sync_side_effect.called_with = (args, kwargs)
#         raise MyCustomTestException("Patch is working!")
#     mock_fetch_sync_side_effect.called_with = None

#     monkeypatch = pytest.MonkeyPatch()
#     monkeypatch.setattr(market_router, 'fetch_yfinance_history_sync', mock_fetch_sync_side_effect)

#     with pytest.raises(MyCustomTestException, match="Patch is working!"):
#         client.get(f"/api/market/stock/{symbol}/history?period={period}&interval={interval}")

#     assert mock_fetch_sync_side_effect.called_with is not None
#     args_called, kwargs_called = mock_fetch_sync_side_effect.called_with
#     assert args_called == (symbol,)
#     assert kwargs_called == {'period': period, 'interval': interval}

#     monkeypatch.undo()

#     # If the above passes, now try with return_value
#     def mock_fetch_return_local_data(*args, **kwargs):
#         mock_fetch_return_local_data.called_count +=1
#         return local_sample_history_data
#     mock_fetch_return_local_data.called_count = 0

#     monkeypatch.setattr(market_router, 'fetch_yfinance_history_sync', mock_fetch_return_local_data)

#     response = client.get(f"/api/market/stock/{symbol}/history?period={period}&interval={interval}")

#     assert response.status_code == 200
#     data = response.json()
#     assert data["symbol"] == symbol
#     assert data["timeframe"] == f"{period}_{interval}"
#     assert len(data["data"]) == len(local_sample_history_data)
#     assert mock_fetch_return_local_data.called_count == 1

#     mock_redis_object.get.assert_called_once()
#     mock_redis_object.set.assert_called_once()

#     monkeypatch.undo()


def test_get_stock_historical_data_empty(mock_yfinance_empty_history, mock_redis_dependency_override):
    interval = "1d"

    # Define sample history data locally for this test to avoid global state issues
    local_sample_history_data = pd.DataFrame({
        'Open': [2810.0, 2820.0], 'High': [2850.0, 2860.0],
        'Low': [2805.0, 2815.0], 'Close': [2830.0, 2855.0],
        'Volume': [5000000, 5100000]
    }, index=pd.to_datetime([datetime(2023,1,1), datetime(2023,1,2)])) # Use fixed dates

    # mock_redis_dependency_override handles Redis
    mock_redis_object, _ = mock_redis_dependency_override # Unpack the tuple
    mock_redis_object.get.return_value = None # Cache miss for this test run
    mock_redis_object.set = AsyncMock(return_value=True) # Ensure set is an awaitable mock

    # Using pytest.monkeypatch to replace the function
    from backend.api import market_router # Import the module where the function lives

    class MyCustomTestException(Exception): pass

    def mock_fetch_sync_side_effect(*args, **kwargs):
        # This function will replace fetch_yfinance_history_sync
        # We can assert it was called and then raise the exception
        mock_fetch_sync_side_effect.called_with = (args, kwargs)
        raise MyCustomTestException("Patch is working!")
    mock_fetch_sync_side_effect.called_with = None

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(market_router, 'fetch_yfinance_history_sync', mock_fetch_sync_side_effect)

    with pytest.raises(MyCustomTestException, match="Patch is working!"):
        client.get(f"/api/market/stock/{symbol}/history?period={period}&interval={interval}")

    assert mock_fetch_sync_side_effect.called_with is not None
    args_called, kwargs_called = mock_fetch_sync_side_effect.called_with
    assert args_called == (symbol,) # fetch_yfinance_history_sync(symbol, period, interval)
    assert kwargs_called == {'period': period, 'interval': interval}

    monkeypatch.undo() # Important to undo the patch

    # If the above passes, now try with return_value
    def mock_fetch_return_local_data(*args, **kwargs):
        mock_fetch_return_local_data.called_count +=1
        return local_sample_history_data
    mock_fetch_return_local_data.called_count = 0

    monkeypatch.setattr(market_router, 'fetch_yfinance_history_sync', mock_fetch_return_local_data)

    response = client.get(f"/api/market/stock/{symbol}/history?period={period}&interval={interval}")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["timeframe"] == f"{period}_{interval}"
    assert len(data["data"]) == len(local_sample_history_data)
    assert mock_fetch_return_local_data.called_count == 1

    mock_redis_object.get.assert_called_once()
    mock_redis_object.set.assert_called_once()

    monkeypatch.undo()


def test_get_stock_historical_data_empty(mock_yfinance_empty_history, mock_redis_dependency_override):
    """Test when yfinance returns empty history."""
    mock_redis_object, _ = mock_redis_dependency_override # Unpack, though not directly used for assertions on redis obj here
    symbol = "EMPTY.NS"
    from backend.api import market_router

    def mock_fetch_raises_ioerror(*args, **kwargs):
        raise IOError("Empty history from yfinance")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(market_router, 'fetch_yfinance_history_sync', mock_fetch_raises_ioerror)

    response = client.get(f"/api/market/stock/{symbol}/history")

    assert response.status_code == 500
    assert f"Could not fetch historical data for {symbol}" in response.json()["detail"]
    monkeypatch.undo()

# TODO: Add tests for other market endpoints: /index, /forex, /commodity
# These would follow similar patterns:
# - Mock yfinance.Ticker and its .info or .history methods.
# - Test successful responses.
# - Test error conditions (e.g., yfinance failure, invalid symbol if distinguishable).
# - Test caching behavior (more advanced).
# - Ensure Pydantic models correctly parse the data.

# Note: To run these tests, ensure `TestClient` and `pytest` are installed.
# `pip install pytest httpx` (httpx is used by TestClient)
# The `mock_redis_client` fixture is a placeholder for more advanced Redis mocking.
# For now, tests primarily focus on yfinance mocking and basic API responses.
# The actual Redis interaction (and its failure modes) within the app's lifespan
# and request cycle would need more targeted mocking of `app.state.redis`.
# For instance, using `app.dependency_overrides` in pytest fixtures for `get_redis_client`.
