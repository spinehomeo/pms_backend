# api/routes/cases.py
import uuid
from typing import Any, List, Optional, Dict
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select

from api.deps import CurrentUser, SessionDep
from models.cases_model import (
    PatientCase, PatientCaseCreate, PatientCaseUpdate, PatientCasePublic, CasesPublic,
)
from models.doctor_preferences_model import DoctorCaseFieldPreference, STANDARD_FIELDS
from models.patients_model import Patient
from models.appointments_model import Appointment
from models.prescriptions_model import Prescription
from models.login_model import Message
from utils.enum_service import EnumService

router = APIRouter(prefix="/cases", tags=["📋 Cases"])


def generate_case_number(doctor_id: uuid.UUID, case_date: date, session: SessionDep) -> str:
    """
    Generate case number in format: C-MMMYY-001
    Example: C-JAN26-001
    """
    # Month abbreviations
    month_names = [
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
    ]
    
    month_abbr = month_names[case_date.month - 1]
    year_short = str(case_date.year)[-2:]  # Last 2 digits of year
    
    # Count cases for this doctor in this month-year
    case_count = session.exec(
        select(func.count())
        .select_from(PatientCase)
        .where(
            PatientCase.doctor_id == doctor_id,
            func.extract('year', PatientCase.case_date) == case_date.year,
            func.extract('month', PatientCase.case_date) == case_date.month
        )
    ).one()
    
    sequence = case_count + 1
    
    return f"C-{month_abbr}{year_short}-{sequence:03d}"


def validate_case_fields(
    doctor_id: uuid.UUID, 
    case_data: Dict[str, Any], 
    session: SessionDep
) -> Dict[str, Any]:
    """
    Validate case fields against doctor's preferences and check required fields.
    """
    # Get doctor's field preferences
    preferences = session.exec(
        select(DoctorCaseFieldPreference).where(
            DoctorCaseFieldPreference.doctor_id == doctor_id
        )
    ).all()
    
    # Create a dictionary of preferences by field name
    pref_dict = {pref.field_name: pref for pref in preferences}
    
    # Check required fields
    for pref in preferences:
        if pref.is_required and pref.is_enabled:
            field_value = case_data.get(pref.field_name)
            if field_value is None or (isinstance(field_value, str) and field_value.strip() == ""):
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field '{pref.display_name}' is missing or empty"
                )
    
    # Filter custom_fields to only include enabled custom fields
    custom_fields = case_data.get("custom_fields")
    if custom_fields:
        # Get enabled custom fields (non-standard fields)
        standard_field_names = {f["field_name"] for f in STANDARD_FIELDS}
        enabled_custom_fields = [
            pref.field_name for pref in preferences 
            if pref.field_name not in standard_field_names
            and pref.is_enabled
        ]
        
        # Filter custom_fields
        validated_custom = {
            field_name: value 
            for field_name, value in custom_fields.items() 
            if field_name in enabled_custom_fields
        }
        case_data["custom_fields"] = validated_custom or None
    
    return case_data


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
        .order_by(PatientCase.case_date.desc())
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
    
    # Populate patient names
    response_cases = []
    for case in cases:
        case_response = PatientCasePublic.model_validate(case)
        case_response.patient_name = case.patient.full_name if case.patient else None
        case_response.patient_phone = case.patient.phone if case.patient else None
        case_response.patient_city = case.patient.city if case.patient else None
        response_cases.append(case_response)
    
    return CasesPublic(data=response_cases, count=count)


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
    
    case_response = PatientCasePublic.model_validate(case)
    case_response.patient_name = case.patient.full_name if case.patient else None
    case_response.patient_phone = case.patient.phone if case.patient else None
    case_response.patient_city = case.patient.city if case.patient else None
    return case_response


@router.post("/", response_model=PatientCasePublic)
def create_case(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    case_in: PatientCaseCreate
) -> Any:
    """
    Create new case with dynamic fields.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create cases")
    
    # Verify patient belongs to doctor
    patient = session.get(Patient, case_in.patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # If appointment_id provided, validate it belongs to this doctor and patient
    if case_in.appointment_id:
        appointment = session.get(Appointment, case_in.appointment_id)
        if not appointment or appointment.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if appointment.patient_id != case_in.patient_id:
            raise HTTPException(status_code=400, detail="Appointment does not belong to this patient")
    
    # Generate case number in new format: C-MMMYY-001
    case_number = generate_case_number(current_user.id, date.today(), session)
    
    # Validate case fields
    case_dict = case_in.model_dump(exclude_unset=True)
    validate_case_fields(current_user.id, case_dict, session)
    
    # Validate status if provided
    if case_dict.get("status"):
        if not EnumService.validate_value(session, "CaseStatus", case_dict["status"], current_user.id):
            raise HTTPException(status_code=400, detail=f"Invalid case status: {case_dict['status']}")
    
    # Prepare case data
    case_data = {
        **case_dict,
        "doctor_id": current_user.id,
        "case_number": case_number
    }
    
    case = PatientCase.model_validate(case_data)
    session.add(case)
    session.commit()
    session.refresh(case)
    
    # Update patient's last visit date
    patient.last_visit_date = case.case_date
    session.add(patient)
    session.commit()
    
    case_response = PatientCasePublic.model_validate(case)
    case_response.patient_name = case.patient.full_name if case.patient else None
    case_response.patient_phone = case.patient.phone if case.patient else None
    case_response.patient_city = case.patient.city if case.patient else None
    return case_response


@router.put("/{case_id}", response_model=PatientCasePublic)
def update_case(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID,
    case_in: PatientCaseUpdate
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
    
    # Validate case fields
    case_dict = case_in.model_dump(exclude_unset=True)
    validate_case_fields(current_user.id, case_dict, session)
    
    # Validate status if provided
    if case_dict.get("status"):
        if not EnumService.validate_value(session, "CaseStatus", case_dict["status"], current_user.id):
            raise HTTPException(status_code=400, detail=f"Invalid case status: {case_dict['status']}")
    
    # Update case
    for field_name, value in case_dict.items():
        if value is not None:
            setattr(case, field_name, value)
    
    session.add(case)
    session.commit()
    session.refresh(case)
    
    case_response = PatientCasePublic.model_validate(case)
    case_response.patient_name = case.patient.full_name if case.patient else None
    case_response.patient_phone = case.patient.phone if case.patient else None
    case_response.patient_city = case.patient.city if case.patient else None
    return case_response


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