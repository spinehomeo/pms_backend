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
    DoctorFollowUpFieldPreference,
    STANDARD_FIELDS,
    FOLLOWUP_STANDARD_FIELDS
)
from models.login_model import Message

router = APIRouter(prefix="/doctor-preferences", tags=["⚙️ Doctor Preferences"])


def get_field_preference_model(form_type: str):
    """Get the appropriate field preference model based on form type"""
    if form_type == "cases":
        return DoctorCaseFieldPreference
    elif form_type == "followups":
        return DoctorFollowUpFieldPreference
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid form_type. Use 'cases' or 'followups'"
        )


def get_standard_fields(form_type: str):
    """Get the standard fields definition based on form type"""
    if form_type == "cases":
        return STANDARD_FIELDS
    elif form_type == "followups":
        return FOLLOWUP_STANDARD_FIELDS
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid form_type. Use 'cases' or 'followups'"
        )


@router.post("/initialize-standard-fields")
def initialize_standard_fields(
    session: SessionDep,
    current_user: CurrentUser,
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Initialize standard fields for a doctor.
    
    Query Parameters:
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    
    This should be called when a doctor first sets up their account.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can set preferences")
    
    FieldModel = get_field_preference_model(form_type)
    standard_fields = get_standard_fields(form_type)
    
    # Check if already initialized for this form type
    existing_count = session.exec(
        select(func.count()).where(
            FieldModel.doctor_id == current_user.id
        )
    ).one()
    
    if existing_count > 0:
        return Message(message=f"Standard {form_type} fields already initialized")
    
    # Create preferences for standard fields
    for i, field_def in enumerate(standard_fields):
        preference = FieldModel(
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
    return Message(message=f"Standard {form_type} fields initialized successfully")


@router.get("/fields", response_model=List[dict])
def get_doctor_fields(
    session: SessionDep,
    current_user: CurrentUser,
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Get all enabled fields configured for the current doctor.
    
    Query Parameters:
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access preferences")
    
    FieldModel = get_field_preference_model(form_type)
    
    preferences = session.exec(
        select(FieldModel).where(
            (FieldModel.doctor_id == current_user.id) & (FieldModel.is_enabled == True)
        ).order_by(FieldModel.position)
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


@router.get("/fields/all", response_model=List[dict])
def get_all_fields(
    session: SessionDep,
    current_user: CurrentUser,
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Get ALL fields for doctor:
    - Standard fields (enabled or disabled)
    - Custom fields
    
    Query Parameters:
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    
    Frontend can use this to show toggle switches and manage preferences.
    """
    if not current_user.is_doctor:
        raise HTTPException(
            status_code=403,
            detail="Only doctors can access preferences"
        )

    FieldModel = get_field_preference_model(form_type)
    standard_fields = get_standard_fields(form_type)

    # Fetch all doctor preferences
    preferences = session.exec(
        select(FieldModel).where(
            FieldModel.doctor_id == current_user.id
        )
    ).all()

    # Convert to dict for easy lookup
    pref_dict = {
        pref.field_name: pref
        for pref in preferences
    }

    result = []

    # Add STANDARD fields
    for i, field in enumerate(standard_fields):
        pref = pref_dict.get(field["field_name"])
        result.append({
            "field_name": field["field_name"],
            "display_name": field["display_name"],
            "field_type": field["field_type"],
            "is_required": pref.is_required if pref else field["default_required"],
            "is_enabled": pref.is_enabled if pref else False,
            "position": pref.position if pref else i,
            "is_custom": False,
            "config": pref.config if pref else {}
        })

    # Add CUSTOM fields
    custom_fields = [
        pref for pref in preferences
        if pref.field_name not in [f["field_name"] for f in standard_fields]
    ]

    for pref in custom_fields:
        result.append({
            "field_name": pref.field_name,
            "display_name": pref.display_name,
            "field_type": pref.field_type,
            "is_required": pref.is_required,
            "is_enabled": pref.is_enabled,
            "position": pref.position,
            "is_custom": True,
            "config": pref.config or {}
        })

    # Sort by position
    result.sort(key=lambda x: x["position"])

    return result


@router.post("/fields/{field_name}/toggle")
def toggle_field(
    session: SessionDep,
    current_user: CurrentUser,
    field_name: str,
    enabled: bool = Query(True),
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Enable or disable a field for the doctor.
    
    Query Parameters:
    - enabled: true to enable, false to disable (default: true)
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update preferences")
    
    FieldModel = get_field_preference_model(form_type)
    standard_fields = get_standard_fields(form_type)
    
    # Check if it's a standard field
    is_standard = any(f["field_name"] == field_name for f in standard_fields)
    if not is_standard:
        raise HTTPException(
            status_code=400,
            detail="Only standard fields can be toggled. Custom fields can be deleted."
        )
    
    # Find the preference
    preference = session.exec(
        select(FieldModel).where(
            (FieldModel.doctor_id == current_user.id) & (FieldModel.field_name == field_name)
        )
    ).first()
    
    if not preference:
        # Create a new preference if it doesn't exist
        field_def = next((f for f in standard_fields if f["field_name"] == field_name), None)
        if not field_def:
            raise HTTPException(status_code=404, detail="Field not found")
        
        # Get next position
        max_position = session.exec(
            select(func.max(FieldModel.position)).where(
                FieldModel.doctor_id == current_user.id
            )
        ).one() or 0
        
        preference = FieldModel(
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
    is_required: bool = False,
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Add a custom field for the doctor.
    
    Query Parameters:
    - field_name: Field identifier (alphanumeric + underscores only)
    - display_name: Display name for the field
    - field_type: Field type (text, textarea, number, date, select, etc.)
    - is_required: Whether field is required (default: false)
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add custom fields")
    
    FieldModel = get_field_preference_model(form_type)
    
    # Validate field name (no spaces, alphanumeric + underscores)
    if not field_name.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Field name can only contain letters, numbers, and underscores"
        )
    
    # Check if field already exists
    existing = session.exec(
        select(FieldModel).where(
            (FieldModel.doctor_id == current_user.id) & (FieldModel.field_name == field_name)
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Field already exists")
    
    # Get next position
    max_position = session.exec(
        select(func.max(FieldModel.position)).where(
            FieldModel.doctor_id == current_user.id
        )
    ).one() or 0
    
    preference = FieldModel(
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


@router.put("/fields/custom/{field_name}")
def edit_custom_field(
    field_name: str,
    session: SessionDep,
    current_user: CurrentUser,
    display_name: Optional[str] = None,
    field_type: Optional[str] = None,
    is_required: Optional[bool] = None,
    config: Optional[Dict[str, Any]] = None,
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Edit an existing custom field.
    Only custom fields can be edited.
    
    Query Parameters:
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    """
    if not current_user.is_doctor:
        raise HTTPException(
            status_code=403,
            detail="Only doctors can edit custom fields"
        )

    FieldModel = get_field_preference_model(form_type)
    standard_fields = get_standard_fields(form_type)

    # Prevent editing standard fields
    is_standard = any(
        f["field_name"] == field_name
        for f in standard_fields
    )

    if is_standard:
        raise HTTPException(
            status_code=400,
            detail="Standard fields cannot be edited"
        )

    preference = session.exec(
        select(FieldModel).where(
            (FieldModel.doctor_id == current_user.id) & (FieldModel.field_name == field_name)
        )
    ).first()

    if not preference:
        raise HTTPException(
            status_code=404,
            detail="Custom field not found"
        )

    # Update fields if provided
    if display_name is not None:
        preference.display_name = display_name

    if field_type is not None:
        preference.field_type = field_type

    if is_required is not None:
        preference.is_required = is_required

    if config is not None:
        preference.config = config

    preference.updated_at = utc_now()

    session.add(preference)
    session.commit()
    session.refresh(preference)

    return {
        "message": "Custom field updated successfully",
        "field": {
            "field_name": preference.field_name,
            "display_name": preference.display_name,
            "field_type": preference.field_type,
            "is_required": preference.is_required,
            "config": preference.config
        }
    }


@router.delete("/fields/{field_name}")
def delete_custom_field(
    session: SessionDep,
    current_user: CurrentUser,
    field_name: str,
    form_type: str = Query("cases", description="Form type: 'cases' or 'followups'")
) -> Any:
    """
    Delete a custom field (only custom fields, not standard ones).
    
    Query Parameters:
    - form_type: "cases" for case fields, "followups" for follow-up fields (default: "cases")
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete fields")
    
    FieldModel = get_field_preference_model(form_type)
    standard_fields = get_standard_fields(form_type)
    
    # Check if it's a standard field
    is_standard = any(f["field_name"] == field_name for f in standard_fields)
    if is_standard:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete standard fields. Use toggle to disable instead."
        )
    
    preference = session.exec(
        select(FieldModel).where(
            (FieldModel.doctor_id == current_user.id) & (FieldModel.field_name == field_name)
        )
    ).first()
    
    if not preference:
        raise HTTPException(status_code=404, detail="Field not found")
    
    session.delete(preference)
    session.commit()
    
    return Message(message="Custom field deleted")
