from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Load environment variables from .env, useful for local dev when not using Docker Compose env vars
# In production/docker, environment variables should be passed directly to the container
load_dotenv(dotenv_path="../../.env") # Assuming .env is in project root

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback construction if DATABASE_URL is not explicitly set
    # This is useful if POSTGRES_USER etc. are set but not the full URL
    # (e.g. by some PaaS or older docker-compose setups)
    DB_USER = os.getenv("POSTGRES_USER", "user")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    DB_HOST = os.getenv("POSTGRES_HOST", "postgres_db") # 'postgres_db' for Docker Compose
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "fingyan_db")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print(f"DATABASE_URL not found in env, constructed: {DATABASE_URL}") # For debugging

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set and could not be constructed.")

# The connect_args is often used for SQLite, but can be used for other options if needed.
# For PostgreSQL, common arguments like SSL might be passed here or in the URL.
engine = create_engine(DATABASE_URL) # connect_args={"check_same_thread": False} is for SQLite only

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from where it's defined (i.e., db_models.py)
from ..models.db_models import Base

def get_db():
    """
    Dependency to get a database session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables (useful for initial setup without Alembic, or for tests)
# In a production app, Alembic should handle migrations.
def create_database_tables():
    """
    Creates all tables in the database.
    This should ideally be handled by Alembic migrations in a production environment.
    """
    # Import all models here before calling create_all to ensure they are registered with Base
    from ..models import db_models # This will make SQLAlchemy aware of User, Portfolio, Holding
    # Assuming Base is defined in db_models and all models inherit from it.
    try:
        print(f"Attempting to create tables with engine for URL: {DATABASE_URL}")
        db_models.Base.metadata.create_all(bind=engine)
        print("Database tables checked/created (if they didn't exist).")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        print("Ensure the database server is running and accessible, and the DATABASE_URL is correct.")
        raise

# If you run this script directly (e.g., python -m backend.services.database_service)
if __name__ == "__main__":
    print("Running database service setup...")
    # The following line is dangerous if you have existing data and no migration strategy.
    # create_database_tables()
    print("If you need to create tables, uncomment the call to create_database_tables() or use Alembic.")
    print(f"Database URL configured: {DATABASE_URL}")
    # Test connection
    try:
        with engine.connect() as connection:
            print("Successfully connected to the database.")
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
