# api/routes/cases.py
import uuid
from typing import Any, List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select

from api.deps import CurrentUser, SessionDep
from models.cases_model import (
    PatientCase, PatientCaseCreate, PatientCasePublic, CasesPublic,
)
from models.patients_model import Patient
from models.prescriptions_model import Prescription
from models.login_model import Message

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/", response_model=CasesPublic)
def read_cases(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Any:
    """
    Retrieve cases with filtering options.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access cases")
    
    # Base query
    count_statement = (
        select(func.count())
        .select_from(PatientCase)
        .where(PatientCase.doctor_id == current_user.id)
    )
    
    statement = (
        select(PatientCase)
        .where(PatientCase.doctor_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    
    # Apply filters
    if patient_id:
        # Verify patient belongs to doctor
        patient = session.get(Patient, patient_id)
        if not patient or patient.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        count_statement = count_statement.where(PatientCase.patient_id == patient_id)
        statement = statement.where(PatientCase.patient_id == patient_id)
    
    if from_date:
        count_statement = count_statement.where(PatientCase.case_date >= from_date)
        statement = statement.where(PatientCase.case_date >= from_date)
    
    if to_date:
        count_statement = count_statement.where(PatientCase.case_date <= to_date)
        statement = statement.where(PatientCase.case_date <= to_date)
    
    count = session.exec(count_statement).one()
    cases = session.exec(statement).all()
    
    return CasesPublic(data=cases, count=count)


@router.get("/{case_id}", response_model=PatientCasePublic)
def read_case(
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID
) -> Any:
    """
    Get case by ID with patient details.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access cases")
    
    case = session.get(PatientCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    
    return case


@router.post("/", response_model=PatientCasePublic)
def create_case(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    case_in: PatientCaseCreate
) -> Any:
    """
    Create new case.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create cases")
    
    # Verify patient belongs to doctor
    patient = session.get(Patient, case_in.patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Generate case number
    today = date.today()
    year_month = today.strftime("%Y-%m")
    
    # Count cases for this month to generate sequential number
    case_count = session.exec(
        select(func.count())
        .select_from(PatientCase)
        .where(
            PatientCase.doctor_id == current_user.id,
            func.extract('year', PatientCase.case_date) == today.year,
            func.extract('month', PatientCase.case_date) == today.month
        )
    ).one()
    
    case_number = f"CASE-{year_month}-{case_count + 1:03d}"
    
    case_data = case_in.model_dump()
    case_data.update({
        "doctor_id": current_user.id,
        "case_number": case_number
    })
    
    case = PatientCase.model_validate(case_data)
    session.add(case)
    session.commit()
    session.refresh(case)
    
    # Update patient's last visit date
    patient.last_visit_date = case.case_date
    session.add(patient)
    session.commit()
    
    return case


@router.put("/{case_id}", response_model=PatientCasePublic)
def update_case(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID,
    case_in: PatientCaseCreate
) -> Any:
    """
    Update a case.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update cases")
    
    case = session.get(PatientCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this case")
    
    # Verify patient belongs to doctor if changing patient
    if case_in.patient_id != case.patient_id:
        patient = session.get(Patient, case_in.patient_id)
        if not patient or patient.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Patient not found")
    
    update_dict = case_in.model_dump(exclude_unset=True)
    case.sqlmodel_update(update_dict)
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


@router.delete("/{case_id}")
def delete_case(
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID
) -> Message:
    """
    Delete a case.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete cases")
    
    case = session.get(PatientCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this case")
    
    session.delete(case)
    session.commit()
    return Message(message="Case deleted successfully")


@router.get("/{case_id}/prescription")
def get_case_prescription(
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID
) -> Any:
    """
    Get prescription for a case.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access prescriptions")
    
    case = session.get(PatientCase, case_id)
    if not case or case.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    prescription = session.exec(
        select(Prescription).where(Prescription.case_id == case_id)
    ).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="No prescription found for this case")
    
    return prescription