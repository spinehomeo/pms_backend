# api/routes/doctor_preferences.py
import uuid
from typing import Any, List, Optional, Dict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select, func

from api.deps import CurrentUser, SessionDep
from utils.time import utc_now
from models.doctor_preferences_model import (
    DoctorCaseFieldPreference,
    STANDARD_FIELDS
)
from models.login_model import Message

router = APIRouter(prefix="/doctor-preferences", tags=["⚙️ Doctor Preferences"])


@router.post("/initialize-standard-fields")
def initialize_standard_fields(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Initialize standard fields for a doctor.
    This should be called when a doctor first sets up their account.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can set preferences")
    
    # Check if already initialized
    existing_count = session.exec(
        select(func.count()).where(
            DoctorCaseFieldPreference.doctor_id == current_user.id
        )
    ).one()
    
    if existing_count > 0:
        return Message(message="Standard fields already initialized")
    
    # Create preferences for standard fields
    for i, field_def in enumerate(STANDARD_FIELDS):
        preference = DoctorCaseFieldPreference(
            doctor_id=current_user.id,
            field_name=field_def["field_name"],
            display_name=field_def["display_name"],
            field_type=field_def["field_type"],
            is_required=field_def["default_required"],
            is_enabled=True,
            position=i,
            created_at=utc_now()
        )
        session.add(preference)
    
    session.commit()
    return Message(message="Standard fields initialized successfully")


@router.get("/fields", response_model=List[dict])
def get_doctor_fields(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get all fields configured for the current doctor.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access preferences")
    
    preferences = session.exec(
        select(DoctorCaseFieldPreference).where(
            DoctorCaseFieldPreference.doctor_id == current_user.id,
            DoctorCaseFieldPreference.is_enabled == True
        ).order_by(DoctorCaseFieldPreference.position)
    ).all()
    
    return [
        {
            "field_name": pref.field_name,
            "display_name": pref.display_name,
            "field_type": pref.field_type,
            "is_required": pref.is_required,
            "position": pref.position,
            "config": pref.config or {}
        }
        for pref in preferences
    ]


@router.post("/fields/{field_name}/toggle")
def toggle_field(
    session: SessionDep,
    current_user: CurrentUser,
    field_name: str,
    enabled: bool = Query(True)
) -> Any:
    """
    Enable or disable a field for the doctor.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update preferences")
    
    # Check if it's a standard field
    is_standard = any(f["field_name"] == field_name for f in STANDARD_FIELDS)
    if not is_standard:
        raise HTTPException(
            status_code=400,
            detail="Only standard fields can be toggled. Custom fields can be deleted."
        )
    
    # Find the preference
    preference = session.exec(
        select(DoctorCaseFieldPreference).where(
            DoctorCaseFieldPreference.doctor_id == current_user.id,
            DoctorCaseFieldPreference.field_name == field_name
        )
    ).first()
    
    if not preference:
        # Create a new preference if it doesn't exist
        field_def = next((f for f in STANDARD_FIELDS if f["field_name"] == field_name), None)
        if not field_def:
            raise HTTPException(status_code=404, detail="Field not found")
        
        # Get next position
        max_position = session.exec(
            select(func.max(DoctorCaseFieldPreference.position)).where(
                DoctorCaseFieldPreference.doctor_id == current_user.id
            )
        ).one() or 0
        
        preference = DoctorCaseFieldPreference(
            doctor_id=current_user.id,
            field_name=field_name,
            display_name=field_def["display_name"],
            field_type=field_def["field_type"],
            is_required=field_def["default_required"],
            is_enabled=enabled,
            position=max_position + 1,
            created_at=utc_now()
        )
    else:
        preference.is_enabled = enabled
        preference.updated_at = utc_now()
    
    session.add(preference)
    session.commit()
    
    return {"message": f"Field '{field_name}' {'enabled' if enabled else 'disabled'}"}


@router.post("/fields/custom")
def add_custom_field(
    session: SessionDep,
    current_user: CurrentUser,
    field_name: str,
    display_name: str,
    field_type: str = "text",
    is_required: bool = False
) -> Any:
    """
    Add a custom field for the doctor.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add custom fields")
    
    # Validate field name (no spaces, alphanumeric + underscores)
    if not field_name.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Field name can only contain letters, numbers, and underscores"
        )
    
    # Check if field already exists
    existing = session.exec(
        select(DoctorCaseFieldPreference).where(
            DoctorCaseFieldPreference.doctor_id == current_user.id,
            DoctorCaseFieldPreference.field_name == field_name
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Field already exists")
    
    # Get next position
    max_position = session.exec(
        select(func.max(DoctorCaseFieldPreference.position)).where(
            DoctorCaseFieldPreference.doctor_id == current_user.id
        )
    ).one() or 0
    
    preference = DoctorCaseFieldPreference(
        doctor_id=current_user.id,
        field_name=field_name,
        display_name=display_name,
        field_type=field_type,
        is_required=is_required,
        is_enabled=True,
        position=max_position + 1,
        created_at=utc_now()
    )
    
    session.add(preference)
    session.commit()
    
    return {
        "message": "Custom field added",
        "field": {
            "field_name": field_name,
            "display_name": display_name,
            "field_type": field_type,
            "is_required": is_required
        }
    }


@router.delete("/fields/{field_name}")
def delete_custom_field(
    session: SessionDep,
    current_user: CurrentUser,
    field_name: str
) -> Any:
    """
    Delete a custom field (only custom fields, not standard ones).
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete fields")
    
    # Check if it's a standard field
    is_standard = any(f["field_name"] == field_name for f in STANDARD_FIELDS)
    if is_standard:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete standard fields. Use toggle to disable instead."
        )
    
    preference = session.exec(
        select(DoctorCaseFieldPreference).where(
            DoctorCaseFieldPreference.doctor_id == current_user.id,
            DoctorCaseFieldPreference.field_name == field_name
        )
    ).first()
    
    if not preference:
        raise HTTPException(status_code=404, detail="Field not found")
    
    session.delete(preference)
    session.commit()
    
    return Message(message="Custom field deleted")
