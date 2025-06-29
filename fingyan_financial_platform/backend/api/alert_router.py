from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..services import database_service, alert_crud
from ..models import alert_models, db_models # db_models for User dependency if using auth

router = APIRouter()

# Dummy user ID for now, replace with actual authenticated user later
DUMMY_USER_ID = 1
# from .auth import get_current_active_user # Placeholder for auth dependency

@router.post("/", response_model=alert_models.AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: alert_models.AlertCreate,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user) # Auth dependency
):
    """
    Create a new alert for the authenticated user.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID # Using dummy user for now

    # Optional: Add logic to prevent duplicate alerts if necessary
    # existing_alerts = alert_crud.get_db_alerts_for_user(db, user_id=user_id, symbol=alert_in.symbol, is_active=True)
    # for ex_alert in existing_alerts:
    #     if ex_alert.target_price == alert_in.target_price and ex_alert.trigger_when_above == alert_in.trigger_when_above:
    #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Similar active alert already exists.")

    created_alert = alert_crud.create_db_alert(db=db, user_id=user_id, alert_in=alert_in)

    # Map db_model to response_model (Pydantic's orm_mode helps if fields match)
    # Manual mapping for clarity or if transformation is needed:
    return alert_models.AlertResponse(
        id=created_alert.id,
        user_id=created_alert.user_id,
        symbol=created_alert.symbol,
        alert_type=created_alert.alert_type,
        description=created_alert.description,
        target_price=created_alert.target_price,
        trigger_when_above=created_alert.trigger_when_above,
        is_active=created_alert.is_active,
        created_at=created_alert.created_at,
        triggered_at=created_alert.triggered_at
    )

@router.get("/{alert_id}", response_model=alert_models.AlertResponse)
async def read_alert(
    alert_id: int,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Get a specific alert by its ID.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    db_alert = alert_crud.get_db_alert(db, alert_id=alert_id, user_id=user_id)
    if not db_alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    return alert_models.AlertResponse.from_orm(db_alert) # Using from_orm for simplicity

@router.get("/", response_model=List[alert_models.AlertResponse])
async def read_alerts(
    symbol: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Retrieve all alerts for the authenticated user, with optional filters.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    db_alerts = alert_crud.get_db_alerts_for_user(
        db, user_id=user_id, symbol=symbol, is_active=is_active, skip=skip, limit=limit
    )
    return [alert_models.AlertResponse.from_orm(alert) for alert in db_alerts]

@router.put("/{alert_id}", response_model=alert_models.AlertResponse)
async def update_alert_details(
    alert_id: int,
    alert_in: alert_models.AlertUpdate,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Update an alert (e.g., target price, active status).
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    updated_db_alert = alert_crud.update_db_alert(db, alert_id=alert_id, user_id=user_id, alert_in=alert_in)
    if not updated_db_alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found or not owned by user")

    return alert_models.AlertResponse.from_orm(updated_db_alert)

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_by_id(
    alert_id: int,
    db: Session = Depends(database_service.get_db)
    # current_user: db_models.User = Depends(get_current_active_user)
):
    """
    Delete an alert by its ID.
    """
    # user_id = current_user.id
    user_id = DUMMY_USER_ID
    success = alert_crud.delete_db_alert(db, alert_id=alert_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found or not owned by user")
    return None # FastAPI will return 204 No Content

# The actual alert *checking* logic (comparing with market data and triggering)
# would be part of a separate background service/worker, not these REST API endpoints.
# That service would use `alert_crud.get_active_alerts_for_monitoring()` and `alert_crud.mark_alert_triggered()`.
