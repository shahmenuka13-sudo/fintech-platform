from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from ..models import db_models, portfolio_models # API models for input types

# --- Portfolio CRUD ---

def get_db_portfolio(db: Session, user_id: int, portfolio_id: Optional[int] = None, name: Optional[str] = None) -> Optional[db_models.Portfolio]:
    """
    Get a single portfolio by ID or name for a specific user.
    """
    query = db.query(db_models.Portfolio).filter(db_models.Portfolio.user_id == user_id)
    if portfolio_id:
        return query.filter(db_models.Portfolio.id == portfolio_id).first()
    if name:
        return query.filter(db_models.Portfolio.name == name).first()
    return None

def get_db_portfolios_for_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[db_models.Portfolio]:
    """
    Get all portfolios for a specific user with pagination.
    """
    return db.query(db_models.Portfolio)\
             .filter(db_models.Portfolio.user_id == user_id)\
             .offset(skip)\
             .limit(limit)\
             .all()

def create_db_portfolio(db: Session, user_id: int, portfolio_in: portfolio_models.PortfolioCreate) -> db_models.Portfolio:
    """
    Create a new portfolio for a user.
    """
    db_portfolio = db_models.Portfolio(
        name=portfolio_in.name,
        description=portfolio_in.description,
        user_id=user_id
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def update_db_portfolio(
    db: Session,
    portfolio_id: int,
    user_id: int,
    portfolio_in: portfolio_models.PortfolioUpdate
) -> Optional[db_models.Portfolio]:
    """
    Update an existing portfolio for a user.
    """
    db_portfolio = db.query(db_models.Portfolio)\
                     .filter(db_models.Portfolio.id == portfolio_id, db_models.Portfolio.user_id == user_id)\
                     .first()
    if not db_portfolio:
        return None

    update_data = portfolio_in.model_dump(exclude_unset=True) # Get only provided fields
    if "name" in update_data:
        db_portfolio.name = update_data["name"]
    if "description" in update_data:
        db_portfolio.description = update_data["description"]

    # If holdings were part of PortfolioUpdate, logic to update them would go here.
    # For now, name and description are the only updatable fields directly on portfolio.

    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def delete_db_portfolio(db: Session, portfolio_id: int, user_id: int) -> bool:
    """
    Delete a portfolio for a user. Returns True if deleted, False otherwise.
    Holdings associated with this portfolio will also be deleted due to cascade.
    """
    db_portfolio = db.query(db_models.Portfolio)\
                     .filter(db_models.Portfolio.id == portfolio_id, db_models.Portfolio.user_id == user_id)\
                     .first()
    if not db_portfolio:
        return False

    db.delete(db_portfolio)
    db.commit()
    return True

# --- Holdings CRUD ---

def get_db_holding(db: Session, portfolio_id: int, symbol: str) -> Optional[db_models.Holding]:
    """
    Get a specific holding within a portfolio by its symbol.
    """
    return db.query(db_models.Holding)\
             .filter(db_models.Holding.portfolio_id == portfolio_id, db_models.Holding.symbol == symbol)\
             .first()

def get_db_holdings_for_portfolio(db: Session, portfolio_id: int) -> List[db_models.Holding]:
    """
    Get all holdings for a specific portfolio.
    """
    return db.query(db_models.Holding)\
             .filter(db_models.Holding.portfolio_id == portfolio_id)\
             .all()

def add_or_update_db_holding(
    db: Session,
    portfolio_id: int,
    asset_in: portfolio_models.PortfolioAssetUpdate # Pydantic model for input
) -> db_models.Holding:
    """
    Add a new holding to a portfolio or update an existing one.
    """
    db_holding = get_db_holding(db, portfolio_id=portfolio_id, symbol=asset_in.symbol)

    if db_holding: # Update existing holding
        db_holding.quantity = asset_in.quantity
        db_holding.average_buy_price = asset_in.average_buy_price
        # Potentially update last_transaction_date here if that field exists
    else: # Create new holding
        db_holding = db_models.Holding(
            portfolio_id=portfolio_id,
            symbol=asset_in.symbol,
            quantity=asset_in.quantity,
            average_buy_price=asset_in.average_buy_price
        )
        db.add(db_holding)

    db.commit()
    db.refresh(db_holding)
    return db_holding

def remove_db_holding(db: Session, portfolio_id: int, symbol: str) -> bool:
    """
    Remove a holding from a portfolio. Returns True if deleted, False otherwise.
    """
    db_holding = get_db_holding(db, portfolio_id=portfolio_id, symbol=symbol)
    if not db_holding:
        return False

    db.delete(db_holding)
    db.commit()
    return True

# --- User CRUD (Minimal for now, to support portfolio linking) ---
# This would typically be in a separate user_crud.py and involve password hashing etc.

def get_db_user(db: Session, user_id: int) -> Optional[db_models.User]:
    return db.query(db_models.User).filter(db_models.User.id == user_id).first()

def get_db_user_by_username(db: Session, username: str) -> Optional[db_models.User]:
    return db.query(db_models.User).filter(db_models.User.username == username).first()

def create_db_user(db: Session, username: str, email: str, hashed_password: str) -> db_models.User:
    """
    Creates a dummy user. In a real app, use proper user creation logic.
    """
    # Check if user already exists
    existing_user = get_db_user_by_username(db, username)
    if existing_user:
        # In a real app, you'd raise an HTTPException or handle this appropriately
        print(f"User {username} already exists.")
        return existing_user # or raise error

    db_user = db_models.User(username=username, email=email, hashed_password=hashed_password, is_active=1)
    db.add(db_user)
    # Removed db.commit() and db.refresh() - to be handled by the caller / unit of work
    # db.commit()
    # db.refresh(db_user)
    print(f"Added user {username} to session.") # Log action
    return db_user

# Function to create a dummy user if it doesn't exist (for dev purposes)
def create_dummy_user_if_not_exists(db: Session, user_id: int = 1, username: str = "dummyuser"):
    user = get_db_user(db, user_id)
    if not user:
        print(f"Dummy user with ID {user_id} not found, creating...")
        # In a real app, password should be properly hashed. This is a placeholder.
        user = create_db_user(db, username=username, email=f"{username}@example.com", hashed_password="hashed_dummy_password")
        # The caller (lifespan event in main.py) will handle commit.
        # If refresh is needed after commit, caller handles it too.
        return user # Return the new user object (uncommitted yet by this function)
    print(f"Dummy user with ID {user_id} ('{user.username}') already exists.")
    return user


# Example of how this might be called during app startup or a test setup:
# from .database_service import SessionLocal
# def init_db():
#     db = SessionLocal()
#     create_dummy_user_if_not_exists(db, user_id=DUMMY_USER_ID)
#     db.close()Tool output for `create_file_with_block`:
