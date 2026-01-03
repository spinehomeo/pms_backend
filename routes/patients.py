# api/routes/patients.py
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select

from api.deps import CurrentUser, SessionDep
from models.patients_model import (
    Patient, PatientCreate, PatientUpdate, PatientPublic, PatientsPublic,
    PatientGender,
)
from models.appointments_model import Appointment
from models.cases_model import PatientCase
from models.login_model import Message

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=PatientsPublic)
def read_patients(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, min_length=1, max_length=100)
) -> Any:
    """
    Retrieve patients with optional search.
    """
    # Only doctors can access patients
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access patients")
    
    # Base query for current doctor's patients
    count_statement = (
        select(func.count())
        .select_from(Patient)
        .where(Patient.doctor_id == current_user.id)
    )
    
    statement = (
        select(Patient)
        .where(Patient.doctor_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    
    # Add search filter if provided
    if search:
        search_filter = f"%{search}%"
        count_statement = count_statement.where(
            Patient.full_name.ilike(search_filter) |
            Patient.phone.ilike(search_filter) |
            Patient.email.ilike(search_filter)
        )
        statement = statement.where(
            Patient.full_name.ilike(search_filter) |
            Patient.phone.ilike(search_filter) |
            Patient.email.ilike(search_filter)
        )
    
    count = session.exec(count_statement).one()
    patients = session.exec(statement).all()
    
    return PatientsPublic(data=patients, count=count)


@router.get("/{patient_id}", response_model=PatientPublic)
def read_patient(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID
) -> Any:
    """
    Get patient by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access patients")
    
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Ensure doctor can only access their own patients
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this patient")
    
    return patient


@router.post("/", response_model=PatientPublic)
def create_patient(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_in: PatientCreate
) -> Any:
    """
    Create new patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create patients")
    
    # Check if patient with same email already exists for this doctor
    if patient_in.email:
        existing = session.exec(
            select(Patient).where(
                Patient.doctor_id == current_user.id,
                Patient.email == patient_in.email
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Patient with this email already exists"
            )
    
    patient = Patient.model_validate(
        patient_in,
        update={"doctor_id": current_user.id}
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientPublic)
def update_patient(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
    patient_in: PatientUpdate
) -> Any:
    """
    Update a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update patients")
    
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this patient")
    
    # Check email uniqueness if being updated
    if patient_in.email and patient_in.email != patient.email:
        existing = session.exec(
            select(Patient).where(
                Patient.doctor_id == current_user.id,
                Patient.email == patient_in.email,
                Patient.id != patient_id
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Another patient with this email already exists"
            )
    
    update_dict = patient_in.model_dump(exclude_unset=True)
    patient.sqlmodel_update(update_dict)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.delete("/{patient_id}")
def delete_patient(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID
) -> Message:
    """
    Delete a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete patients")
    
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this patient")
    
    # Cascade delete will handle related cases, appointments, etc.
    session.delete(patient)
    session.commit()
    return Message(message="Patient deleted successfully")


@router.get("/{patient_id}/stats")
def get_patient_stats(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID
) -> Any:
    """
    Get statistics for a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access patient stats")
    
    patient = session.get(Patient, patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Count cases
    cases_count = session.exec(
        select(func.count())
        .select_from(PatientCase)
        .where(PatientCase.patient_id == patient_id)
    ).one()
    
    # Count appointments
    appointments_count = session.exec(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.patient_id == patient_id)
    ).one()
    
    # Get last visit date
    last_appointment = session.exec(
        select(Appointment.appointment_date)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_date.desc())
    ).first()
    
    return {
        "patient_id": patient_id,
        "total_cases": cases_count,
        "total_appointments": appointments_count,
        "last_visit_date": last_appointment,
        "age": patient.age
    }