# api/routes/medicines.py - GLOBAL CATALOG VERSION
import uuid
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select, or_

from api.deps import CurrentUser, SessionDep
from models.medicines_model import (
    Medicine, MedicineCreate, MedicinePublic, MedicinesPublic,
    MedicineUpdate, DoctorMedicinePreference,
)
from models.login_model import Message
from models.prescriptions_model import PrescriptionMedicine
from models.users_model import User
from utils.enum_service import EnumService

router = APIRouter(prefix="/medicines", tags=["💊 Medicines"])


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_medicine_enums(session, medicine_data: dict):
    """
    Validate medicine enum fields against dynamic enum system.
    Values are validated against existing database enums (case-insensitive).
    Enums: FormEnum, ManufacturerEnum, ScaleEnum (already fully seeded)
    
    Raises HTTPException if any enum value is invalid.
    """
    # Normalize input to lowercase for consistent comparison
    if medicine_data.get("potency_scale"):
        scale_value = str(medicine_data["potency_scale"]).lower()
        if not EnumService.validate_value(session, "ScaleEnum", scale_value):
            valid_scales = [opt.value for opt in EnumService.get_global_options(session, "ScaleEnum")]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid potency_scale '{medicine_data['potency_scale']}'. Valid values: {', '.join(valid_scales)}"
            )
        # Update to normalized value
        medicine_data["potency_scale"] = scale_value
    
    # Validate form (case-insensitive)
    if medicine_data.get("form"):
        form_value = str(medicine_data["form"]).lower()
        if not EnumService.validate_value(session, "FormEnum", form_value):
            valid_forms = [opt.value for opt in EnumService.get_global_options(session, "FormEnum")]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid form '{medicine_data['form']}'. Valid values: {', '.join(valid_forms)}"
            )
        # Update to normalized value
        medicine_data["form"] = form_value
    
    # Validate manufacturer (case-insensitive)
    if medicine_data.get("manufacturer"):
        mfg_value = str(medicine_data["manufacturer"]).lower()
        if not EnumService.validate_value(session, "ManufacturerEnum", mfg_value):
            valid_manufacturers = [opt.value for opt in EnumService.get_global_options(session, "ManufacturerEnum")]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid manufacturer '{medicine_data['manufacturer']}'. Valid values: {', '.join(valid_manufacturers)}"
            )
        # Update to normalized value
        medicine_data["manufacturer"] = mfg_value


@router.get("/all", response_model=MedicinesPublic)
def read_all_medicines(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Retrieve ALL medicines from catalog without any filters or pagination.
    Useful for dropdowns, initial autocomplete load, or full catalog display.
    
    Note: Use with caution if catalog is very large (1000+ medicines).
    For large catalogs, use the paginated /medicines/ endpoint instead.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access medicines")
    
    # Get all medicines, ordered by name and potency
    statement = select(Medicine).order_by(Medicine.name, Medicine.potency)
    medicines = session.exec(statement).all()
    
    # Get favorites for current doctor to enrich response
    medicine_ids = [m.id for m in medicines]
    if medicine_ids:
        preferences = session.exec(
            select(DoctorMedicinePreference)
            .where(
                DoctorMedicinePreference.doctor_id == current_user.id,
                DoctorMedicinePreference.medicine_id.in_(medicine_ids)
            )
        ).all()
        
        pref_map = {p.medicine_id: p.is_favorite for p in preferences}
        
        # Add is_favorite to response
        medicines_with_favorite = []
        for m in medicines:
            medicine_data = {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "potency": m.potency or "",
                "potency_scale": m.potency_scale or "C",
                "form": m.form or "Globules",
                "manufacturer": m.manufacturer,
                "created_by_doctor_id": m.created_by_doctor_id,
                "created_at": m.created_at or datetime.utcnow(),
                "is_verified": m.is_verified if m.is_verified is not None else False,
                "is_favorite": pref_map.get(m.id, False)
            }
            medicines_with_favorite.append(MedicinePublic(**medicine_data))
        
        return MedicinesPublic(data=medicines_with_favorite, count=len(medicines))
    
    return MedicinesPublic(data=medicines, count=len(medicines))

# `read_medicines` endpoint removed — use `/medicines/` paginated or `/medicines/search` advanced endpoint instead.


@router.get("/search", response_model=MedicinesPublic)
def advanced_search_medicines(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    potency: Optional[str] = Query(None),
    potency_scale: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    manufacturer: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None, description="UUID or email of creator"),
    is_verified: Optional[bool] = Query(None),
    is_favorite: Optional[bool] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
) -> Any:
    """
    Advanced search - filter by any field combination.
    Favorites from the current doctor are returned at the top of the list.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access medicines")
    
    # Build main query without pagination (will paginate after ordering)
    statement = select(Medicine)
    count_statement = select(func.count()).select_from(Medicine)
    
    # Apply filters
    if name:
        statement = statement.where(Medicine.name.ilike(f"%{name}%"))
        count_statement = count_statement.where(Medicine.name.ilike(f"%{name}%"))
    
    if description:
        statement = statement.where(Medicine.description.ilike(f"%{description}%"))
        count_statement = count_statement.where(Medicine.description.ilike(f"%{description}%"))
    
    if potency:
        statement = statement.where(Medicine.potency.ilike(f"%{potency}%"))
        count_statement = count_statement.where(Medicine.potency.ilike(f"%{potency}%"))
    
    if potency_scale:
        statement = statement.where(Medicine.potency_scale == potency_scale)
        count_statement = count_statement.where(Medicine.potency_scale == potency_scale)
    
    if form:
        statement = statement.where(Medicine.form == form)
        count_statement = count_statement.where(Medicine.form == form)
    
    if manufacturer:
        statement = statement.where(Medicine.manufacturer == manufacturer)
        count_statement = count_statement.where(Medicine.manufacturer == manufacturer)
    
    if created_by:
        # accept either UUID or email/username; try UUID first
        try:
            parsed = uuid.UUID(created_by)
            statement = statement.where(Medicine.created_by_doctor_id == parsed)
            count_statement = count_statement.where(Medicine.created_by_doctor_id == parsed)
        except Exception:
            # treat as email/identifier and lookup user
            user = session.exec(select(User).where(User.email == created_by)).first()
            if not user:
                # no user found -> return empty
                return MedicinesPublic(data=[], count=0)
            statement = statement.where(Medicine.created_by_doctor_id == user.id)
            count_statement = count_statement.where(Medicine.created_by_doctor_id == user.id)
    
    if is_verified is not None:
        statement = statement.where(Medicine.is_verified == is_verified)
        count_statement = count_statement.where(Medicine.is_verified == is_verified)
    
    if from_date:
        statement = statement.where(Medicine.created_at >= from_date)
        count_statement = count_statement.where(Medicine.created_at >= from_date)
    
    if to_date:
        statement = statement.where(Medicine.created_at <= to_date)
        count_statement = count_statement.where(Medicine.created_at <= to_date)
    
    # Handle favorites filter
    has_favorite_filter = False
    if is_favorite is not None:
        has_favorite_filter = True
        if is_favorite:
            statement = (
                statement
                .join(DoctorMedicinePreference)
                .where(
                    DoctorMedicinePreference.doctor_id == current_user.id,
                    DoctorMedicinePreference.is_favorite == True
                )
            )
            count_statement = (
                count_statement
                .join(DoctorMedicinePreference)
                .where(
                    DoctorMedicinePreference.doctor_id == current_user.id,
                    DoctorMedicinePreference.is_favorite == True
                )
            )
        else:
            # Not favorite or no preference
            subquery = (
                select(DoctorMedicinePreference.medicine_id)
                .where(
                    DoctorMedicinePreference.doctor_id == current_user.id,
                    DoctorMedicinePreference.is_favorite == True
                )
            )
            statement = statement.where(Medicine.id.notin_(subquery))
            count_statement = count_statement.where(Medicine.id.notin_(subquery))
    
    # Join with doctor preferences to sort favorites on top (if not already joined)
    if not has_favorite_filter or not is_favorite:
        statement = statement.outerjoin(
            DoctorMedicinePreference, 
            (DoctorMedicinePreference.medicine_id == Medicine.id) &
            (DoctorMedicinePreference.doctor_id == current_user.id)
        )
    
    # Sort: favorites first (coalesce handles NULL values), then by name
    statement = (
        statement
        .order_by(
            func.coalesce(DoctorMedicinePreference.is_favorite, False).desc(),
            Medicine.name
        )
        .offset(skip)
        .limit(limit)
    )
    
    count = session.exec(count_statement).one()
    medicines = session.exec(statement).all()
    
    # Enrich with favorite status
    medicine_ids = [m.id for m in medicines]
    if medicine_ids:
        preferences = session.exec(
            select(DoctorMedicinePreference)
            .where(
                DoctorMedicinePreference.doctor_id == current_user.id,
                DoctorMedicinePreference.medicine_id.in_(medicine_ids)
            )
        ).all()
        
        pref_map = {p.medicine_id: p.is_favorite for p in preferences}
        
        medicines_with_favorite = []
        for m in medicines:
            medicine_data = {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "potency": m.potency or "",
                "potency_scale": m.potency_scale or "C",
                "form": m.form or "Globules",
                "manufacturer": m.manufacturer,
                "created_by_doctor_id": m.created_by_doctor_id,
                "created_at": m.created_at or datetime.utcnow(),
                "is_verified": m.is_verified if m.is_verified is not None else False,
                "is_favorite": pref_map.get(m.id, False)
            }
            medicines_with_favorite.append(MedicinePublic(**medicine_data))
        
        return MedicinesPublic(data=medicines_with_favorite, count=count)
    
    return MedicinesPublic(data=medicines, count=count)


@router.post("/add", response_model=MedicinePublic)
def create_medicine(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    medicine_in: MedicineCreate
) -> Any:
    """
    Add new medicine to global catalog.
    Any doctor can add medicines, but they need admin verification.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add medicines")
    
    # Validate enum fields against dynamic enum system
    medicine_data = medicine_in.model_dump()
    validate_medicine_enums(session, medicine_data)
    
    # Check if medicine already exists (same name + potency + form)
    existing = session.exec(
        select(Medicine)
        .where(
            Medicine.name == medicine_in.name,
            Medicine.potency == medicine_in.potency,
            Medicine.potency_scale == medicine_in.potency_scale,
            Medicine.form == medicine_in.form
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Medicine '{medicine_in.name}' with potency {medicine_in.potency}{medicine_in.potency_scale} and form {medicine_in.form} already exists"
        )
    
    # Create medicine
    medicine_data = medicine_in.model_dump()
    medicine_data["created_by_doctor_id"] = current_user.id
    medicine_data["is_verified"] = False  # Needs admin verification
    
    medicine = Medicine.model_validate(medicine_data)
    session.add(medicine)
    session.commit()
    session.refresh(medicine)
    
    # Auto-add to doctor's preferences
    preference = DoctorMedicinePreference(
        doctor_id=current_user.id,
        medicine_id=medicine.id,
        usage_count=0,
        is_favorite=False
    )
    session.add(preference)
    session.commit()
    
    return medicine


# `quick_add_medicine` endpoint removed — quick-add flow is handled via prescriptions creation which creates/returns medicines as needed.


@router.get("/{medicine_id}", response_model=MedicinePublic)
def read_medicine(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: uuid.UUID = Path(..., description="Medicine ID")
) -> Any:
    """
    Get medicine by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access medicines")
    
    medicine = session.get(Medicine, medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    return medicine


@router.put("/{medicine_id}", response_model=MedicinePublic)
def update_medicine(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: uuid.UUID,
    medicine_in: MedicineUpdate
) -> Any:
    """
    Update medicine details.
    Only the doctor who created it (or admin) can update.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update medicines")
    
    medicine = session.get(Medicine, medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # Check authorization (creator or admin)
    if medicine.created_by_doctor_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only the creator or admin can update this medicine"
        )
    
    # Validate enum fields against dynamic enum system
    update_dict = medicine_in.model_dump(exclude_unset=True)
    validate_medicine_enums(session, update_dict)
    
    # Update fields
    medicine.sqlmodel_update(update_dict)
    
    session.add(medicine)
    session.commit()
    session.refresh(medicine)
    
    return medicine


@router.delete("/{medicine_id}")
def delete_medicine(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: uuid.UUID
) -> Message:
    """
    Delete medicine from catalog.
    Only admin/superuser can delete medicines.
    """
    # Check authorization - only superusers can delete medicines
    if current_user.is_doctor or current_user.is_staff:
        raise HTTPException(
            status_code=422,
            detail="Doctor and staff cannot delete medicines"
        )
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=422,
            detail="Only admins can delete medicines"
        )
    
    medicine = session.get(Medicine, medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # Check if medicine is used in any prescriptions
    prescription_count = session.exec(
        select(func.count())
        .select_from(PrescriptionMedicine)
        .where(PrescriptionMedicine.medicine_id == medicine_id)
    ).one()
    
    if prescription_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete medicine. It is used in {prescription_count} prescription(s)"
        )
    
    session.delete(medicine)
    session.commit()
    
    return Message(message="Medicine deleted successfully")


@router.post("/bulk", response_model=MedicinesPublic)
def create_medicines_bulk(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    medicines_in: List[MedicineCreate]
) -> Any:
    """
    Add multiple medicines in bulk.
    Skips duplicates and returns all created medicines.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add medicines")
    
    if not medicines_in:
        raise HTTPException(status_code=400, detail="No medicines provided")
    
    if len(medicines_in) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 medicines per bulk operation")
    
    created_medicines = []
    skipped_count = 0
    
    for medicine_in in medicines_in:
        # Check if medicine already exists
        existing = session.exec(
            select(Medicine)
            .where(
                Medicine.name == medicine_in.name,
                Medicine.potency == medicine_in.potency,
                Medicine.potency_scale == medicine_in.potency_scale,
                Medicine.form == medicine_in.form
            )
        ).first()
        
        if existing:
            skipped_count += 1
            continue
        
        # Create new medicine
        medicine_data = medicine_in.model_dump()
        medicine_data["created_by_doctor_id"] = current_user.id
        medicine_data["is_verified"] = False
        
        medicine = Medicine.model_validate(medicine_data)
        session.add(medicine)
        created_medicines.append(medicine)
    
    session.commit()
    
    # Refresh all created medicines to get IDs
    for medicine in created_medicines:
        session.refresh(medicine)
    
    return MedicinesPublic(
        data=created_medicines,
        count=len(created_medicines)
    )


@router.post("/{medicine_id}/favorite")
def toggle_favorite(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: uuid.UUID
) -> Message:
    """
    Toggle medicine as favorite for current doctor.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can mark favorites")
    
    medicine = session.get(Medicine, medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # Check if preference exists
    preference = session.exec(
        select(DoctorMedicinePreference)
        .where(
            DoctorMedicinePreference.doctor_id == current_user.id,
            DoctorMedicinePreference.medicine_id == medicine_id
        )
    ).first()
    
    if preference:
        # Toggle favorite
        preference.is_favorite = not preference.is_favorite
        session.add(preference)
    else:
        # Create new preference
        preference = DoctorMedicinePreference(
            doctor_id=current_user.id,
            medicine_id=medicine_id,
            is_favorite=True
        )
        session.add(preference)
    
    session.commit()
    
    status = "added to" if preference.is_favorite else "removed from"
    return Message(message=f"Medicine {status} favorites")