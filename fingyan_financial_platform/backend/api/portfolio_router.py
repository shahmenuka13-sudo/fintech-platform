from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..services import database_service
from ..models import db_models, portfolio_models
from ..services.portfolio_crud import (
    create_db_portfolio, get_db_portfolio, get_db_portfolios_for_user,
    update_db_portfolio, delete_db_portfolio,
    add_or_update_db_holding, get_db_holding, remove_db_holding,
    get_db_holdings_for_portfolio
)
# Placeholder for market data service to enrich portfolio later
# from ..services.market_data_service import get_current_prices_for_symbols

router = APIRouter()

# Dummy user ID for now, replace with actual authenticated user later
DUMMY_USER_ID = 1

@router.post("/", response_model=portfolio_models.PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_in: portfolio_models.PortfolioCreate,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user) # Placeholder for auth
):
    """
    Create a new portfolio for the authenticated user.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID # Using dummy user for now
    db_portfolio = get_db_portfolio(db, user_id=user_id, name=portfolio_in.name)
    if db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Portfolio with name '{portfolio_in.name}' already exists for this user."
        )

    created_portfolio = create_db_portfolio(db=db, user_id=user_id, portfolio_in=portfolio_in)
    # Manually construct holdings for response as create_db_portfolio returns db_models.Portfolio
    return portfolio_models.PortfolioResponse(
        id=created_portfolio.id,
        name=created_portfolio.name,
        description=created_portfolio.description,
        user_id=created_portfolio.user_id,
        created_at=created_portfolio.created_at,
        updated_at=created_portfolio.updated_at,
        holdings=[] # Initially empty
    )

@router.get("/{portfolio_id}", response_model=portfolio_models.PortfolioDetailResponse) # Using Detail for potential enrichment
async def read_portfolio(
    portfolio_id: int,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Get a specific portfolio by its ID.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    db_portfolio = get_db_portfolio(db, portfolio_id=portfolio_id, user_id=user_id)
    if not db_portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    # Convert DB holdings to Pydantic model and enrich them (simplified enrichment for now)
    enriched_holdings = []
    total_invested_value = 0.0
    # current_total_value = 0.0 # This would require fetching live prices

    db_holdings = get_db_holdings_for_portfolio(db, portfolio_id=db_portfolio.id)
    # symbols_to_fetch = [h.symbol for h in db_holdings]
    # live_prices = await get_current_prices_for_symbols(symbols_to_fetch, db_provider_or_similar) # Needs market service

    for holding in db_holdings:
        invested_value = holding.quantity * holding.average_buy_price
        total_invested_value += invested_value

        # current_price = live_prices.get(holding.symbol) # Fetch from market data service
        # current_value_asset = current_price * holding.quantity if current_price else None
        # profit_loss = (current_value_asset - invested_value) if current_value_asset else None
        # profit_loss_percent = (profit_loss / invested_value * 100) if profit_loss and invested_value else None
        # if current_value_asset: current_total_value += current_value_asset

        enriched_holdings.append(portfolio_models.EnrichedHoldingAsset(
            symbol=holding.symbol,
            quantity=holding.quantity,
            average_buy_price=holding.average_buy_price,
            # current_price=current_price,
            # current_value=current_value_asset,
            # profit_loss=profit_loss,
            # profit_loss_percent=profit_loss_percent
        ))

    # overall_profit_loss = current_total_value - total_invested_value
    # overall_profit_loss_percent = (overall_profit_loss / total_invested_value * 100) if overall_profit_loss and total_invested_value else 0.0

    return portfolio_models.PortfolioDetailResponse(
        id=db_portfolio.id,
        name=db_portfolio.name,
        description=db_portfolio.description,
        user_id=db_portfolio.user_id,
        created_at=db_portfolio.created_at,
        updated_at=db_portfolio.updated_at,
        holdings=enriched_holdings,
        total_invested_value=total_invested_value,
        # current_total_value=current_total_value,
        # overall_profit_loss=overall_profit_loss,
        # overall_profit_loss_percent=overall_profit_loss_percent
    )


@router.get("/", response_model=List[portfolio_models.PortfolioResponse])
async def read_portfolios(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Retrieve all portfolios for the authenticated user.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    db_portfolios = get_db_portfolios_for_user(db, user_id=user_id, skip=skip, limit=limit)

    response_portfolios = []
    for p in db_portfolios:
        # For simplicity, not including detailed holdings in the list view
        # db_holdings = get_db_holdings_for_portfolio(db, portfolio_id=p.id)
        # portfolio_api_holdings = [portfolio_models.HoldingAsset.from_orm(h) for h in db_holdings]
        response_portfolios.append(portfolio_models.PortfolioResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            user_id=p.user_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
            holdings=[] # Or fetch and map if needed for list view
        ))
    return response_portfolios

@router.put("/{portfolio_id}", response_model=portfolio_models.PortfolioResponse)
async def update_portfolio_details(
    portfolio_id: int,
    portfolio_in: portfolio_models.PortfolioUpdate,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Update portfolio details (name, description).
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    updated_db_portfolio = update_db_portfolio(db, portfolio_id=portfolio_id, user_id=user_id, portfolio_in=portfolio_in)
    if not updated_db_portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or not owned by user")

    # db_holdings = get_db_holdings_for_portfolio(db, portfolio_id=updated_db_portfolio.id)
    # portfolio_api_holdings = [portfolio_models.HoldingAsset.from_orm(h) for h in db_holdings]

    return portfolio_models.PortfolioResponse(
        id=updated_db_portfolio.id,
        name=updated_db_portfolio.name,
        description=updated_db_portfolio.description,
        user_id=updated_db_portfolio.user_id,
        created_at=updated_db_portfolio.created_at,
        updated_at=updated_db_portfolio.updated_at,
        holdings=[] # Or fetch and map
    )

@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_by_id(
    portfolio_id: int,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Delete a portfolio by its ID.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    success = delete_db_portfolio(db, portfolio_id=portfolio_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or not owned by user")
    return None # FastAPI will return 204 No Content

# --- Holdings Management ---

@router.post("/{portfolio_id}/holdings", response_model=portfolio_models.PortfolioAssetResponse)
async def add_or_update_holding_in_portfolio(
    portfolio_id: int,
    asset_in: portfolio_models.PortfolioAssetUpdate,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Add a new asset to a portfolio or update an existing one (quantity, average price).
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    # First, verify portfolio ownership (or just existence for dummy user)
    db_portfolio = get_db_portfolio(db, portfolio_id=portfolio_id, user_id=user_id)
    if not db_portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or not owned by user")

    db_holding = add_or_update_db_holding(db, portfolio_id=portfolio_id, asset_in=asset_in)
    return portfolio_models.PortfolioAssetResponse(
        portfolio_id=db_holding.portfolio_id,
        symbol=db_holding.symbol,
        quantity=db_holding.quantity,
        average_buy_price=db_holding.average_buy_price
    )

@router.delete("/{portfolio_id}/holdings/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_holding_from_portfolio(
    portfolio_id: int,
    symbol: str,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Remove an asset (holding) from a portfolio by its symbol.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    db_portfolio = get_db_portfolio(db, portfolio_id=portfolio_id, user_id=user_id)
    if not db_portfolio: # Check ownership/existence
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or not owned by user")

    success = remove_db_holding(db, portfolio_id=portfolio_id, symbol=symbol)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with symbol '{symbol}' not found in portfolio.")
    return None

# Note: `get_current_active_user` would be the dependency for OAuth2.
# Enrichment of portfolio data with live market prices is a TODO and requires market_router/service integration.
# The `PortfolioAsset.from_orm(h)` might need `Config.orm_mode = True` in Pydantic models,
# but it's often cleaner to map explicitly if shapes differ or logic is needed.
# For now, manual mapping is used.
# The responses for portfolio list/update could also include holdings if desired, but kept minimal here.Tool output for `create_file_with_block`:
