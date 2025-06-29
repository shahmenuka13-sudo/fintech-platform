import os # For SENTRY_DSN environment variable
from fastapi import FastAPI
from redis import asyncio as aioredis # Use asyncio version of redis
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import sentry_sdk

from .api import market_router, portfolio_router, alert_router, news_router, predict_router # Added predict_router

from .services.database_service import SessionLocal, engine, create_database_tables # For DB init
from .models import db_models # For table creation and user model
from .services.portfolio_crud import create_dummy_user_if_not_exists # For dummy user

# In-memory cache for simplicity in this example, replace with Redis in production
# For a real Redis setup, you'd initialize the client here or in a separate config module.
# Example: redis_client = aioredis.from_url("redis://localhost", decode_responses=True)

# --- Sentry Initialization ---
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # Adjust in production!
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # Adjust in production!
        profiles_sample_rate=1.0,
        # Enable FastAPI integration
        integrations=[
            sentry_sdk.integrations.fastapi.FastApiIntegration(),
            sentry_sdk.integrations.asgi.AsgiIntegration(),
            # Add other integrations like sqlalchemy, redis if needed
            sentry_sdk.integrations.sqlalchemy.SqlalchemyIntegration(),
            sentry_sdk.integrations.redis.RedisIntegration(),
        ],
        send_default_pii=True, # Be careful with PII in production
        # Environment can be set here or via SENTRY_ENVIRONMENT env var
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
    )
    print("Sentry initialized.")
else:
    print("SENTRY_DSN not found. Sentry will not be initialized.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    print("Application startup...")
    # 1. Create database tables (if they don't exist)
    #    In a production setup with Alembic, you might not run create_all() here,
    #    but rely on migrations being applied separately.
    #    For development and ease of setup, it's included.
    print("Checking/creating database tables...")
    # db_models.Base.metadata.create_all(bind=engine) # This is one way
    create_database_tables() # Using the function from database_service

    # 2. Create dummy user for portfolio operations if it doesn't exist
    #    This is for development convenience before full auth is implemented.
    print("Checking/creating dummy user...")
    db: Session = SessionLocal()
    try:
        create_dummy_user_if_not_exists(db, user_id=1, username="dummyuser") # DUMMY_USER_ID is 1 in portfolio_router
        db.commit() # Commit any changes made by create_dummy_user
    except Exception as e:
        print(f"Error creating dummy user: {e}")
        db.rollback() # Rollback on error
    finally:
        db.close()
    print("Dummy user check complete.")

    # 3. Initialize Redis connection
    print("Initializing Redis connection...")
    app.state.redis = await aioredis.from_url("redis://redis_cache:6379/0", decode_responses=True)
    print("Redis connection initialized.")

    yield

    # Shutdown:
    print("Application shutdown...")
    # Close Redis connection
    if hasattr(app.state, 'redis') and app.state.redis:
        await app.state.redis.close()
        print("Redis connection closed.")
    print("Shutdown complete.")

app = FastAPI(
    title="Fingyan Financial Platform API",
    description="API services for the Fingyan Financial Platform, providing market data, portfolio management, alerts, and AI predictions.",
    version="0.1.0",
    lifespan=lifespan # Use the lifespan context manager
)

# Include routers
app.include_router(market_router.router, prefix="/api/market", tags=["Market Data"])
app.include_router(portfolio_router.router, prefix="/api/portfolio", tags=["Portfolio Management"])
app.include_router(alert_router.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(news_router.router, prefix="/api/news", tags=["News & Sentiment"])
app.include_router(predict_router.router, prefix="/api/predict", tags=["AI Predictions"])


@app.get("/health", tags=["General"])
async def health_check():
    """
    Health check endpoint to verify if the API is running.
    """
    # Check Redis connection
    redis_ping = False
    try:
        if hasattr(app.state, 'redis') and app.state.redis:
            redis_ping = await app.state.redis.ping()
    except Exception as e:
        print(f"Redis health check failed: {e}") # Log the error
        redis_ping = False

    return {"status": "healthy", "redis_connected": redis_ping}

# To run this app (assuming this file is in backend/main.py):
# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
# Ensure 'redis_cache' is resolvable, e.g., via docker-compose.
# If running locally without Docker for backend, change "redis://redis_cache:6379/0"
# to "redis://localhost:6379/0" or your actual Redis URL.
