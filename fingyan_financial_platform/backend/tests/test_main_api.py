from fastapi.testclient import TestClient
import pytest # Pytest will be installed by CI workflow from requirements.txt

# Adjust the import path based on how pytest discovers your app.
# If running pytest from the project root (`fingyan_financial_platform/`),
# and `backend/` is a directory directly under it, this import should work.
from backend.main import app # Main FastAPI app instance

# If the above import fails due to path issues in local pytest runs vs CI,
# you might need to adjust sys.path or use relative imports if tests are structured as a sub-package,
# or ensure PYTHONPATH includes the project root.
# Example of sys.path adjustment if needed (usually not for CI if structure is good):
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) # Adds project root
# from backend.main import app


# Create a TestClient instance
# This client will be used by test functions.
# It's good practice to define it once if multiple tests use the same app setup.
# For more complex setups (e.g. needing specific dependencies or startup events),
# use pytest fixtures.
client = TestClient(app)


def test_health_check():
    """
    Test the /health endpoint.
    It should return a 200 OK status and a JSON response with "status": "healthy".
    """
    response = client.get("/health")
    assert response.status_code == 200

    json_response = response.json()
    assert json_response["status"] == "healthy"

    # Check for redis_connected key, but don't assert its value strictly here
    # as it depends on a live Redis connection which might not be available during all test runs
    # (especially simple unit tests without docker-compose up).
    # The CI environment for tests typically doesn't run docker-compose services alongside tests unless configured.
    assert "redis_connected" in json_response
    # If you have a fixture that ensures Redis is available for tests, you can assert True:
    # assert json_response["redis_connected"] == True


def test_read_root_redirect():
    """
    FastAPI by default serves docs at /docs and /redoc.
    Testing if root path `/` perhaps redirects or gives 404 if not defined.
    Our app doesn't define `/`, so it should be a 404.
    If you added a root path handler, test that instead.
    """
    response = client.get("/")
    assert response.status_code == 404 # Assuming no route is defined for "/"
    # If you expect a redirect to /docs, the status code would be different (e.g. 307)
    # and you'd check response.headers['location'].


# Example of a test for a non-existent route
def test_non_existent_route():
    response = client.get("/non_existent_path_xyz")
    assert response.status_code == 404

# To run these tests locally (ensure pytest and FastAPI test client dependencies are installed):
# 1. Navigate to the root of your project (`fingyan_financial_platform`).
# 2. Ensure backend code can be imported (e.g. `export PYTHONPATH=.`)
# 3. Run: `pytest` or `pytest backend/tests`

# Note on testing services that connect to DB/Redis:
# - For pure unit tests, you'd mock these external dependencies.
# - For integration tests, you might use test-specific DBs/Redis instances,
#   often spun up via docker-compose using a separate `docker-compose.test.yml`
#   or by using libraries like `pytest-docker`.
# The current /health check test is simple and its assertion on redis_connected is loose
# to accommodate environments where Redis might not be running during the test.
# The main.py lifespan event tries to connect to Redis; if it fails, redis_connected will be false.
# TestClient will run the lifespan events.
# If Redis is essential for most tests, you'd need to ensure it's available.
# For now, the health check test is primarily for the API endpoint itself.
