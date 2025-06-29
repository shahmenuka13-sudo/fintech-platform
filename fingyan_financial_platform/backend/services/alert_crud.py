from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Union, Sequence
from datetime import datetime

from ..models import db_models, alert_models # API models for input types

# --- Alert CRUD ---

def get_db_alert(db: Session, alert_id: int, user_id: int) -> Optional[db_models.Alert]:
    """
    Get a specific alert by its ID for a given user.
    """
    return db.query(db_models.Alert)\
             .filter(db_models.Alert.id == alert_id, db_models.Alert.user_id == user_id)\
             .first()

def get_db_alerts_for_user(
    db: Session,
    user_id: int,
    symbol: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[db_models.Alert]:
    """
    Get all alerts for a specific user, with optional filters for symbol and active status.
    Includes pagination.
    """
    query = db.query(db_models.Alert).filter(db_models.Alert.user_id == user_id)

    if symbol:
        query = query.filter(db_models.Alert.symbol == symbol)
    if is_active is not None:
        query = query.filter(db_models.Alert.is_active == is_active)

    return query.order_by(db_models.Alert.created_at.desc())\
                .offset(skip)\
                .limit(limit)\
                .all()

def create_db_alert(db: Session, user_id: int, alert_in: alert_models.AlertCreate) -> db_models.Alert:
    """
    Create a new alert for a user.
    """
    # Basic validation for price alert type is handled by Pydantic model.
    # More complex validation for 'indicator' type alerts would go here if implemented.

    db_alert = db_models.Alert(
        user_id=user_id,
        symbol=alert_in.symbol,
        alert_type=alert_in.alert_type,
        description=alert_in.description,
        is_active=alert_in.is_active,
        # Price alert specific fields
        target_price=alert_in.target_price if alert_in.alert_type == "price" else None,
        trigger_when_above=alert_in.trigger_when_above if alert_in.alert_type == "price" else None,
        # TODO: Add fields for 'indicator' type alerts if/when they are fully defined.
        # indicator_name=alert_in.indicator_name,
        # indicator_condition=alert_in.indicator_condition,
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def update_db_alert(
    db: Session,
    alert_id: int,
    user_id: int,
    alert_in: alert_models.AlertUpdate
) -> Optional[db_models.Alert]:
    """
    Update an existing alert for a user.
    Only fields present in alert_in (and not None) will be updated.
    """
    db_alert = get_db_alert(db, alert_id=alert_id, user_id=user_id)
    if not db_alert:
        return None

    update_data = alert_in.model_dump(exclude_unset=True) # Get only fields explicitly set in the input

    for key, value in update_data.items():
        setattr(db_alert, key, value)

    # If target_price is updated, ensure trigger_when_above is also appropriately set or validated
    if "target_price" in update_data and db_alert.alert_type == "price":
        if "trigger_when_above" not in update_data and db_alert.trigger_when_above is None:
            # This case should ideally be caught by Pydantic model on AlertUpdate if made stricter
            # For now, we assume if target_price is set, trigger_when_above should exist or be set.
            pass # Or raise error / require it.

    db.commit()
    db.refresh(db_alert)
    return db_alert

def delete_db_alert(db: Session, alert_id: int, user_id: int) -> bool:
    """
    Delete an alert for a user. Returns True if deleted, False otherwise.
    """
    db_alert = get_db_alert(db, alert_id=alert_id, user_id=user_id)
    if not db_alert:
        return False

    db.delete(db_alert)
    db.commit()
    return True

def mark_alert_triggered(db: Session, alert_id: int, triggered_at: datetime = datetime.utcnow()) -> Optional[db_models.Alert]:
    """
    Marks an alert as triggered and deactivates it (by default, can be changed).
    This would typically be called by a separate monitoring service.
    """
    db_alert = db.query(db_models.Alert).filter(db_models.Alert.id == alert_id).first()
    if not db_alert:
        return None

    db_alert.triggered_at = triggered_at
    db_alert.is_active = False # Deactivate after triggering; user can re-activate if desired

    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_active_alerts_for_monitoring(db: Session) -> List[db_models.Alert]:
    """
    Get all active alerts across all users.
    This is intended for a background monitoring service to check against market data.
    """
    return db.query(db_models.Alert).filter(db_models.Alert.is_active == True).all()
