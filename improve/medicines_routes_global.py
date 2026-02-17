# api/routes/medicines.py - GLOBAL CATALOG VERSION
import uuid
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select, or_

from api.deps import CurrentUser, SessionDep
from models.medicines_model import (
    Medicine, MedicineCreate, MedicinePublic, MedicinesPublic,
    MedicineUpdate, DoctorMedicinePreference, QuickAddMedicineRequest
)
from models.login_model import Message

router = APIRouter(prefix="/medicines", tags=["💊 Medicines"])


@router.get("/", response_model=MedicinesPublic)
def read_medicines(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, min_length=1),
    only_favorites: bool = Query(False),
    only_verified: bool = Query(False),
) -> Any:
    """
    Retrieve medicines from global catalog with search and filtering.
    
    - search: Search by medicine name
    - only_favorites: Show only medicines marked as favorite by current doctor
    - only_verified: Show only admin-verified medicines
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access medicines")
    
    # Base query
    statement = select(Medicine).offset(skip).limit(limit)
    count_statement = select(func.count()).select_from(Medicine)
    
    # Apply search filter
    if search:
        search_filter = or_(
            Medicine.name.ilike(f"%{search}%"),
            Medicine.potency.ilike(f"%{search}%")
        )
        statement = statement.where(search_filter)
        count_statement = count_statement.where(search_filter)
    
    # Apply verified filter
    if only_verified:
        statement = statement.where(Medicine.is_verified == True)
        count_statement = count_statement.where(Medicine.is_verified == True)
    
    # Apply favorites filter
    if only_favorites:
        # Join with preferences to get only favorites
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
    
    # Order by name
    statement = statement.order_by(Medicine.name)
    
    # Execute queries
    count = session.exec(count_statement).one()
    medicines = session.exec(statement).all()
    
    # Enrich with favorite status for current doctor
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
            m_dict = m.model_dump()
            m_dict['is_favorite'] = pref_map.get(m.id, False)
            medicines_with_favorite.append(MedicinePublic(**m_dict))
        
        return MedicinesPublic(data=medicines_with_favorite, count=count)
    
    return MedicinesPublic(data=medicines, count=count)


@router.get("/search", response_model=MedicinesPublic)
def search_medicines_autocomplete(
    session: SessionDep,
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
) -> Any:
    """
    Quick search for autocomplete during prescription creation.
    Returns top matches by name and potency.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can search medicines")
    
    statement = (
        select(Medicine)
        .where(
            or_(
                Medicine.name.ilike(f"%{q}%"),
                Medicine.potency.ilike(f"%{q}%")
            )
        )
        .order_by(Medicine.name)
        .limit(limit)
    )
    
    medicines = session.exec(statement).all()
    
    return MedicinesPublic(data=medicines, count=len(medicines))


@router.get("/{medicine_id}", response_model=MedicinePublic)
def read_medicine(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: int = Path(..., description="Medicine ID")
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


@router.post("/", response_model=MedicinePublic)
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


@router.post("/quick-add", response_model=MedicinePublic)
def quick_add_medicine(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    medicine_in: QuickAddMedicineRequest
) -> Any:
    """
    Quick-add medicine during prescription creation.
    Checks for duplicates first, returns existing if found.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add medicines")
    
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
        # Return existing medicine
        return existing
    
    # Create new medicine
    medicine_data = medicine_in.model_dump()
    medicine_data["created_by_doctor_id"] = current_user.id
    medicine_data["is_verified"] = False
    
    medicine = Medicine.model_validate(medicine_data)
    session.add(medicine)
    session.commit()
    session.refresh(medicine)
    
    return medicine


@router.put("/{medicine_id}", response_model=MedicinePublic)
def update_medicine(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: int,
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
    
    # Update fields
    update_dict = medicine_in.model_dump(exclude_unset=True)
    medicine.sqlmodel_update(update_dict)
    
    session.add(medicine)
    session.commit()
    session.refresh(medicine)
    
    return medicine


@router.delete("/{medicine_id}")
def delete_medicine(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: int
) -> Message:
    """
    Delete medicine from catalog.
    Only admin or creator (if not used in prescriptions) can delete.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete medicines")
    
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
    
    # Check authorization
    if medicine.created_by_doctor_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only the creator or admin can delete this medicine"
        )
    
    session.delete(medicine)
    session.commit()
    
    return Message(message="Medicine deleted successfully")


@router.post("/{medicine_id}/favorite")
def toggle_favorite(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: int
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
