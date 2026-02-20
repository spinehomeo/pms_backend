# routes/enums.py
"""
Dynamic enum management API endpoints.

Architecture:
- Admins can create/edit/delete enum types and their options
- Doctors can toggle enum options they want to use
- Staff see dropdown options filtered by their assigned doctor

This is a fully dynamic dropdown system - no hardcoded enums.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query

from api.deps import CurrentUser, SessionDep, get_current_active_superuser, require_doctor_role
from models.users_model import User
from models.enum_option_model import (
    EnumType,
    EnumOption,
    DoctorEnumPreference,
    EnumTypeCreate,
    EnumTypeUpdate,
    EnumTypePublic,
    EnumOptionPublic,
    EnumOptionCreate,
    EnumOptionUpdate,
    EnumOptionToggle,
)
from utils.enum_service import EnumService

router = APIRouter(prefix="/enums", tags=["⚙️ Enums | Dynamic"])


# ============================================================================
# ADMIN: Enum Type Management
# ============================================================================

@router.get("/admin/types", response_model=list[EnumTypePublic])
def list_enum_types(
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> list[EnumType]:
    """
    [ADMIN ONLY] List all registered enum types (system + custom).
    
    System enums (seeded) cannot be deleted, only disabled.
    Returns both active and inactive types for admin visibility.
    """
    return EnumService.get_all_enum_types(session, active_only=False)


@router.post("/admin/types", response_model=EnumTypePublic)
def create_enum_type(
    payload: EnumTypeCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> EnumType:
    """
    [ADMIN ONLY] Create a new enum type (dropdown category).
    
    Example: Create "VisitType" dropdown for visit classification.
    This registers a new dropdown that can then have options added to it.
    
    Args:
        key: Unique identifier (e.g., "VisitType") - alphanumeric + underscores
        label: Human-readable name (e.g., "Visit Type")
        description: What this dropdown is used for
    
    Returns:
        The created EnumType with ID
        
    Raises:
        400: A type with this key already exists
    """
    try:
        return EnumService.create_enum_type(
            session=session,
            key=payload.key,
            label=payload.label,
            description=payload.description,
            created_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/admin/types/{type_id}", response_model=EnumTypePublic)
def update_enum_type(
    type_id: UUID,
    payload: EnumTypeUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> EnumType:
    """
    [ADMIN ONLY] Update an enum type (disable/enable, change label/description).
    
    Cannot change the key (enum_type_key), only the label and description.
    """
    enum_type = session.get(EnumType, type_id)
    if not enum_type:
        raise HTTPException(status_code=404, detail="Enum type not found")
    
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(enum_type, key, value)
    
    session.add(enum_type)
    session.commit()
    session.refresh(enum_type)
    return enum_type


@router.delete("/admin/types/{type_id}")
def delete_enum_type(
    type_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> dict:
    """
    [ADMIN ONLY] Delete an enum type and all its options.
    
    Cannot delete system enums (is_system=True).
    Use PATCH to disable instead of delete.
    """
    try:
        EnumService.delete_enum_type(session, type_id)
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ADMIN: Enum Option Management (CRUD)
# ============================================================================

@router.get("/admin/{enum_type_key}", response_model=list[EnumOptionPublic])
def list_all_options(
    enum_type_key: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
    include_inactive: bool = Query(False, description="Include disabled options"),
) -> list[EnumOption]:
    """
    [ADMIN ONLY] List all options for an enum type.
    
    Returns all active options by default.
    Use include_inactive=true to see disabled options too.
    """
    options = EnumService.get_global_options(
        session, enum_type_key, active_only=not include_inactive
    )
    return options


@router.post("/admin/{enum_type_key}", response_model=EnumOptionPublic)
def create_option(
    enum_type_key: str,
    payload: EnumOptionCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> EnumOption:
    """
    [ADMIN ONLY] Add a new option to an enum type.
    
    Example:
    POST /enums/admin/VisitType
    {
        "value": "Follow Up",
        "label": "Follow Up (Existing patient revisit)",
        "sort_order": 1
    }
    """
    try:
        return EnumService.create_enum_option(
            session=session,
            enum_type_key=enum_type_key,
            value=payload.value,
            label=payload.label,
            sort_order=payload.sort_order or 0,
            created_by=current_user.id,
            is_system=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/admin/option/{option_id}", response_model=EnumOptionPublic)
def update_option(
    option_id: UUID,
    payload: EnumOptionUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> EnumOption:
    """
    [ADMIN ONLY] Update an enum option (label, sort order, active status).
    
    Cannot change the value (the option's key), only its label and display settings.
    """
    option = session.get(EnumOption, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(option, key, value)
    
    session.add(option)
    session.commit()
    session.refresh(option)
    return option


@router.delete("/admin/option/{option_id}")
def delete_option(
    option_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
) -> dict:
    """
    [ADMIN ONLY] Delete an enum option.
    
    Cannot delete system options (is_system=True).
    Use PATCH to disable instead of delete.
    """
    try:
        EnumService.delete_enum_option(session, option_id)
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# DOCTOR: View and customize their enum preferences
# ============================================================================

@router.get("/doctor/all", response_model=dict)
def list_all_enums_with_options(
    session: SessionDep,
    current_user: User = Depends(require_doctor_role),
) -> dict:
    """
    [DOCTOR] Get ALL enum types with their options (filtered by doctor's preferences).
    
    Returns:
    {
        "AppointmentStatus": [
            { "id": "...", "value": "Confirmed", "label": "...", ... },
            { "id": "...", "value": "Pending", "label": "...", ... }
        ],
        "PatientGender": [
            { "id": "...", "value": "Male", "label": "...", ... },
            ...
        ]
    }
    
    Use this endpoint in the frontend to populate all available dropdowns at once.
    All options are filtered by the doctor's preferences (disabled options are excluded).
    """
    enum_dict = EnumService.get_all_enum_types_with_doctor_options(
        session, current_user.id
    )
    
    # Convert to dict of dicts for JSON serialization
    result = {}
    for enum_type_key, options in enum_dict.items():
        result[enum_type_key] = options
    
    return result


@router.get("/doctor/{enum_type_key}", response_model=list[EnumOptionPublic])
def list_doctor_options(
    enum_type_key: str,
    session: SessionDep,
    current_user: User = Depends(require_doctor_role),
) -> list[EnumOption]:
    """
    [DOCTOR] Get options visible to the current doctor.
    
    These are all active global options MINUS any the doctor has disabled.
    Use this endpoint in dropdown components on the frontend.
    
    If doctor has no preferences recorded, all active options are returned.
    """
    return EnumService.get_doctor_options(session, enum_type_key, current_user.id)


@router.post("/doctor/{enum_type_key}", response_model=EnumOptionPublic)
def create_option_as_doctor(
    enum_type_key: str,
    payload: EnumOptionCreate,
    session: SessionDep,
    current_user: User = Depends(require_doctor_role),
) -> EnumOption:
    """
    [DOCTOR] Add a new option to an enum type.
    
    Doctors can contribute new options to shared enum types.
    The option is automatically enabled for the doctor who creates it.
    
    Example:
    POST /enums/doctor/AppointmentStatus
    {
        "value": "Rescheduled",
        "label": "Rescheduled (Appointment moved to later date)",
        "sort_order": 3
    }
    
    Raises:
        400: Enum type not found or option value already exists
    """
    try:
        # Create the option
        option = EnumService.create_enum_option(
            session=session,
            enum_type_key=enum_type_key,
            value=payload.value,
            label=payload.label,
            sort_order=payload.sort_order or 0,
            created_by=current_user.id,
            is_system=False,
        )
        
        # Auto-enable this option for the doctor who created it
        EnumService.set_doctor_preference(
            session=session,
            doctor_id=current_user.id,
            option_id=option.id,
            is_enabled=True,
        )
        
        return option
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/doctor/preferences/{option_id}", response_model=dict)
def toggle_doctor_preference(
    option_id: UUID,
    payload: EnumOptionToggle,
    session: SessionDep,
    current_user: User = Depends(require_doctor_role),
) -> dict:
    """
    [DOCTOR] Toggle an option on/off for the current doctor.
    
    Example:
    POST /enums/doctor/preferences/{option_id}
    {
        "is_enabled": false
    }
    
    This disables an option for this doctor - it won't appear in their
    GET /enums/doctor/{enum_type_key} results anymore.
    
    When is_enabled=true, this essentially resets the preference (removes the toggle).
    """
    try:
        pref = EnumService.set_doctor_preference(
            session=session,
            doctor_id=current_user.id,
            option_id=option_id,
            is_enabled=payload.is_enabled,
        )
        return {
            "option_id": option_id,
            "is_enabled": payload.is_enabled,
            "message": "Preference updated"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/doctor/preferences/list/{enum_type_key}", response_model=dict)
def list_doctor_preferences(
    enum_type_key: str,
    session: SessionDep,
    current_user: User = Depends(require_doctor_role),
) -> dict:
    """
    [DOCTOR] Get detailed view of doctor's preferences for an enum type.
    
    Returns:
    {
        "enum_type_key": "AppointmentStatus",
        "enabled_options": [ { id, value, label, ... } ],
        "disabled_options": [ { id, value, label, ... } ]
    }
    
    Useful for a preferences management UI.
    """
    # Get all global options
    all_options = EnumService.get_global_options(session, enum_type_key, active_only=True)
    
    # Get doctor's preferences
    prefs = EnumService.get_all_doctor_preferences(session, current_user.id, enum_type_key)
    disabled_option_ids = {
        pref.enum_option_id for pref in prefs if not pref.is_enabled
    }
    
    enabled_options = [opt for opt in all_options if opt.id not in disabled_option_ids]
    disabled_options = [opt for opt in all_options if opt.id in disabled_option_ids]
    
    return {
        "enum_type_key": enum_type_key,
        "enabled_options": enabled_options,
        "disabled_options": disabled_options,
    }


# ============================================================================
# STAFF: Query enums filtered by assigned doctor
# ============================================================================

@router.get("/staff/{enum_type_key}", response_model=list[EnumOptionPublic])
def list_options_for_staff(
    enum_type_key: str,
    session: SessionDep,
    current_user: CurrentUser,
    doctor_id: UUID = Query(..., description="ID of the doctor to filter by"),
) -> list[EnumOption]:
    """
    [STAFF] Get enum options filtered by assigned doctor's preferences.
    
    Staff members query dropdowns using the doctor they're assigned to work with.
    The result is filtered to show only options the doctor has enabled.
    
    Query Parameters:
        doctor_id: UUID of the doctor whose preferences to use
    
    Example:
    GET /enums/staff/AppointmentStatus?doctor_id=abc-123-def
    
    Returns options visible to that doctor.
    """
    return EnumService.get_doctor_options(session, enum_type_key, doctor_id)


# ============================================================================
# VALIDATION HELPER (for internal use by other routes)
# ============================================================================

@router.post("/validate")
def validate_enum_value(
    session: SessionDep,
    enum_type: str = Query(..., description="Enum type key"),
    value: str = Query(..., description="Value to validate"),
    doctor_id: Optional[UUID] = Query(None, description="Doctor ID for filtered validation"),
) -> dict:
    """
    Validate that a value is valid for an enum type.
    
    Used by other endpoints to validate user input before saving.
    If doctor_id provided, validates against doctor's filtered options.
    Otherwise validates against all active global options.
    
    Returns:
    {
        "valid": true,
        "message": "Value is valid"
    }
    """
    is_valid = EnumService.validate_value(
        session, enum_type, value, doctor_id
    )
    
    return {
        "valid": is_valid,
        "message": "Value is valid" if is_valid else f"Invalid {enum_type}: {value}"
    }
