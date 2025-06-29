from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
import sqlalchemy as sa # Added for sa.Boolean, sa.text etc.
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

#SQLALCHEMY_DATABASE_URL = "postgresql://user:password@db:5432/mydatabase" # Example for docker
# Fallback for local development if DB_HOST is not set (e.g. running outside docker)
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres_db") # 'postgres_db' is the service name in docker-compose
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "fingyan_db")

#SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# Use a more robust way to get the database URL, potentially from a config service or direct env var
# For now, this is fine for local dev and docker-compose via .env or compose env vars.
# However, the application code should ideally receive this from its environment, not construct it.
# The FastAPI app will get this from environment variables set in docker-compose.yml or K8s.
# For local non-docker execution, an .env file would supply these.

# Let's assume DATABASE_URL will be provided by the environment (e.g. by Docker Compose)
# For local testing or Alembic, you might need a direct way to load this
# DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
# For now, we will define it but note that the actual engine creation will be in database_service.py
# to centralize db connection management.

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False) # Simple username for now
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # Store hashed passwords
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Integer, default=1) # Use Integer for boolean if preferred for some DBs, or Boolean

    portfolios = relationship("Portfolio", back_populates="owner")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_user_portfolio_name'),)


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False) # e.g., "RELIANCE.NS"
    quantity = Column(Float, nullable=False)
    average_buy_price = Column(Float, nullable=False)
    # last_transaction_date = Column(DateTime(timezone=True), server_default=func.now())
    # last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (UniqueConstraint('portfolio_id', 'symbol', name='uq_portfolio_symbol'),)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)

    alert_type = Column(String, default="price", nullable=False) # "price", "indicator", etc.
    description = Column(String, nullable=True)

    # Fields for price alerts
    target_price = Column(Float, nullable=True)
    # True if alert triggers when current price > target_price
    # False if alert triggers when current price < target_price
    trigger_when_above = Column(sa.Boolean, nullable=True)

    # Fields for indicator alerts (conceptual, can be expanded with JSON or more columns)
    # indicator_name = Column(String, nullable=True) # e.g., "RSI_14"
    # indicator_params = Column(JSONB, nullable=True) # e.g., {"period": 14}
    # indicator_condition = Column(String, nullable=True) # e.g., "crosses_above_70" / "gt"
    # indicator_threshold = Column(Float, nullable=True) # e.g., 70

    is_active = Column(sa.Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    triggered_at = Column(DateTime(timezone=True), nullable=True) # Timestamp of last trigger
    # last_checked_at = Column(DateTime(timezone=True), nullable=True) # For monitoring service

    owner = relationship("User") # Define relationship to User if needed for querying user's alerts

    # Potentially a constraint: for a given user and symbol, an alert condition should be unique.
    # E.g., user can't set two alerts for RELIANCE.NS > 2500.
    # This might be too restrictive or complex for now.

# Example of how to create tables (typically done with Alembic migrations)
if __name__ == "__main__":
    # This is for illustrative purposes or direct script execution if needed.
    # In a real app, use Alembic.
    print("Attempting to load DATABASE_URL for table creation demo...")
    DATABASE_URL_DEMO = os.getenv("DATABASE_URL")
    if not DATABASE_URL_DEMO:
        # Construct a fallback if not set, for local demo purposes ONLY
        DATABASE_URL_DEMO = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        print(f"DATABASE_URL not set, using fallback: {DATABASE_URL_DEMO}")
        print("Ensure your PostgreSQL server is running and accessible.")

    # Check if we can even connect
    try:
        engine = create_engine(DATABASE_URL_DEMO)
        with engine.connect() as connection:
            print("Successfully connected to the database for demo.")

        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created (if they didn't exist).")
    except Exception as e:
        print(f"Error connecting to database or creating tables: {e}")
        print("Please ensure your DATABASE_URL is correctly set in your environment or .env file,")
        print("and that the PostgreSQL server is running and accessible.")
        print(f"Using connection string: {DATABASE_URL_DEMO}")

# Note: For migrations, you would set up Alembic.
# Example:
# alembic init alembic
# Edit alembic.ini to point to your database URL.
# Edit alembic/env.py to import your Base and target_metadata = Base.metadata
# alembic revision -m "create_initial_tables"
# alembic upgrade head
