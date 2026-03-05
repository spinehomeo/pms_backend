# routes/onsite_patient.py
"""
Onsite Patient Management Routes
================================

Specialized endpoints for walk-in/onsite patient handling:
- Quick lookup by phone number
- Bulk matching for similar patients
- Onsite patient registration (used before creating full consultation)
- Patient record completion after walk-in

These endpoints support the reception desk workflow:
1. Patient arrives
2. Desk staff searches by phone (GET /patients/onsite/search?phone=...)
3. If not found, quick-register (POST /patients/onsite/quick-register)
4. Doctor completes missing fields after consultation
"""

import uuid
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, or_, and_, SQLModel, Field

from api.deps import get_db, get_current_user
from models.users_model import User
from models.patients_model import Patient, PatientCreate, PatientPublic, DoctorBasicInfo

router = APIRouter(prefix="/patients/onsite", tags=["Onsite Patient Management"])


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class OnsitePatientQuickRegisterIn(SQLModel):
    """
    Quick registration for walk-in patients.
    Full_name and phone are required; everything else is optional.
    """
    full_name: str = Field(max_length=255)
    phone: str = Field(max_length=20)
    gender: Optional[str] = Field(default="unknown", max_length=20)
    cnic: Optional[str] = Field(default=None, max_length=15)
    date_of_birth: Optional[date] = None
    email: Optional[str] = Field(default=None, max_length=255)
    phone_secondary: Optional[str] = Field(default=None, max_length=20)
    residential_address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    occupation: Optional[str] = Field(default=None, max_length=255)
    referred_by: Optional[str] = Field(default=None, max_length=255)
    medical_history: Optional[str] = None
    drug_allergies: Optional[str] = None
    family_history: Optional[str] = None
    current_medications: Optional[str] = None
    notes: Optional[str] = None
    payment_status: bool = Field(default=False)


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class PatientMatchResponse(PatientPublic):
    """Response for patient lookup/match"""
    is_match_by_phone: bool
    is_match_by_name: bool
    match_score: float  # 0.0-1.0; 1.0 = exact match


class PatientQuickRegisterResponse(PatientPublic):
    """Response after quick registration"""
    is_temp_cnic: bool  # True if auto-generated


# ============================================================================
# HELPERS
# ============================================================================

def _calculate_match_score(
    existing: Patient,
    phone: Optional[str] = None,
    full_name: Optional[str] = None,
) -> tuple[float, bool, bool]:
    """
    Calculate similarity score between existing patient and search criteria.
    
    Returns:
        (score: float, phone_match: bool, name_match: bool)
    
    Scoring:
        - Exact phone match: +0.9
        - Exact name match: +0.7
        - Partial name match: +0.4
    """
    score = 0.0
    phone_match = False
    name_match = False

    if phone and existing.phone == phone:
        score += 0.9
        phone_match = True

    if full_name and existing.full_name:
        if existing.full_name.lower() == full_name.lower():
            score += 0.7
            name_match = True
        elif (
            existing.full_name.lower().split()[0] == full_name.lower().split()[0]
            and len(full_name.lower().split()) > 0
        ):
            # Match on first name only
            score += 0.4

    return min(score, 1.0), phone_match, name_match


def _calculate_age(date_of_birth: Optional[date]) -> Optional[int]:
    """
    Calculate age from date of birth.
    
    Args:
        date_of_birth: Patient's date of birth
        
    Returns:
        Age in years, or None if no date of birth provided
    """
    if not date_of_birth:
        return None
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/search",
    response_model=List[PatientMatchResponse],
    summary="Search onsite patients by phone or name",
    description=(
        "Quick lookup for walk-in patients. Searches by phone (exact) or name (partial/fuzzy). "
        "Returns up to 10 matches sorted by relevance. Prevents accidentally creating duplicates "
        "for the same person with typos."
    ),
)
def search_onsite_patients(
    phone: Optional[str] = Query(None, max_length=20),
    full_name: Optional[str] = Query(None, max_length=255),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PatientMatchResponse]:
    """
    Search for existing onsite patients.

    Query Parameters:
        phone: Patient phone number (exact match)
        full_name: Patient name (partial/case-insensitive)

    At least one parameter is required.
    Results scoped to current doctor only.
    """

    if not phone and not full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'phone' or 'full_name' is required.",
        )

    # Build query scoped to current doctor
    search_conditions = []

    if phone:
        search_conditions.append(Patient.phone == phone)
    if full_name:
        # Case-insensitive partial match
        search_conditions.append(Patient.full_name.ilike(f"%{full_name}%"))

    # Doctor must always match (AND), search filters are OR'd together
    if search_conditions:
        query = select(Patient).where(
            and_(
                Patient.doctor_id == current_user.id,
                or_(*search_conditions) if len(search_conditions) > 1 else search_conditions[0]
            )
        )
    else:
        query = select(Patient).where(Patient.doctor_id == current_user.id)

    patients = session.exec(query).all()

    # Calculate match scores and sort by relevance
    results = []
    for patient in patients[:10]:  # Limit to 10 results
        score, phone_match, name_match = _calculate_match_score(
            patient,
            phone=phone,
            full_name=full_name,
        )
        if score > 0:  # Only include results with some relevance
            results.append(
                PatientMatchResponse(
                    id=patient.id,
                    full_name=patient.full_name,
                    phone=patient.phone,
                    gender=patient.gender,
                    date_of_birth=patient.date_of_birth,
                    email=patient.email,
                    cnic=patient.cnic,
                    phone_secondary=patient.phone_secondary,
                    residential_address=patient.residential_address,
                    city=patient.city,
                    occupation=patient.occupation,
                    referred_by=patient.referred_by,
                    medical_history=patient.medical_history,
                    drug_allergies=patient.drug_allergies,
                    family_history=patient.family_history,
                    current_medications=patient.current_medications,
                    notes=patient.notes,
                    payment_status=patient.payment_status,
                    created_date=patient.created_date,
                    last_visit_date=patient.last_visit_date,
                    is_active=patient.is_active,
                    age=_calculate_age(patient.date_of_birth),
                    doctor=DoctorBasicInfo(
                        id=patient.doctor.id,
                        full_name=patient.doctor.full_name,
                        specialization=patient.doctor.specialization,
                        phone=patient.doctor.phone,
                        clinic_name=patient.doctor.clinic_name,
                        clinic_address=patient.doctor.clinic_address,
                    ),
                    is_match_by_phone=phone_match,
                    is_match_by_name=name_match,
                    match_score=score,
                )
            )

    # Sort by score (highest first)
    results.sort(key=lambda x: x.match_score, reverse=True)

    return results


@router.post(
    "/quick-register",
    response_model=PatientQuickRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Quick-register a new walk-in patient",
    description=(
        "Fast registration for new walk-in patients. Requires only full_name and phone. "
        "If CNIC is not provided, auto-generates a temporary CNIC (TEMP-...) that the doctor "
        "can update later. Gender defaults to 'unknown'."
    ),
)
def quick_register_patient(
    payload: OnsitePatientQuickRegisterIn,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientQuickRegisterResponse:
    """
    Quick-register a walk-in patient.

    Minimal fields required:
        - full_name (string)
        - phone (string)

    All other fields optional. CNIC auto-generated if not provided.
    """

    # Check if patient already exists by phone
    existing = session.exec(
        select(Patient).where(
            (Patient.phone == payload.phone) &
            (Patient.doctor_id == current_user.id)
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Patient with phone {payload.phone} already exists. "
            f"Use the patient ID or search endpoint instead.",
        )

    # Auto-generate CNIC if not provided
    is_temp_cnic = not payload.cnic
    cnic = payload.cnic or f"TEMP-{uuid.uuid4().hex[:10].upper()}"

    patient = Patient(
        id=uuid.uuid4(),
        doctor_id=current_user.id,
        full_name=payload.full_name,
        phone=payload.phone,
        gender=payload.gender or "unknown",
        cnic=cnic,
        date_of_birth=payload.date_of_birth,
        email=payload.email,
        phone_secondary=payload.phone_secondary,
        residential_address=payload.residential_address,
        city=payload.city,
        occupation=payload.occupation,
        referred_by=payload.referred_by,
        medical_history=payload.medical_history,
        drug_allergies=payload.drug_allergies,
        family_history=payload.family_history,
        current_medications=payload.current_medications,
        notes=payload.notes,
        payment_status=False,
        is_active=True,
        created_date=date.today(),
    )

    try:
        session.add(patient)
        session.commit()
        session.refresh(patient)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register patient: {str(e)}",
        )

    return PatientQuickRegisterResponse(
        id=patient.id,
        full_name=patient.full_name,
        phone=patient.phone,
        gender=patient.gender,
        cnic=patient.cnic,
        is_temp_cnic=is_temp_cnic,
        created_date=patient.created_date,
        last_visit_date=patient.last_visit_date,
        is_active=patient.is_active,
        age=_calculate_age(patient.date_of_birth),
        date_of_birth=patient.date_of_birth,
        email=patient.email,
        phone_secondary=patient.phone_secondary,
        residential_address=patient.residential_address,
        city=patient.city,
        occupation=patient.occupation,
        referred_by=patient.referred_by,
        medical_history=patient.medical_history,
        drug_allergies=patient.drug_allergies,
        family_history=patient.family_history,
        current_medications=patient.current_medications,
        notes=patient.notes,
        payment_status=patient.payment_status,
        doctor=DoctorBasicInfo(
            id=patient.doctor.id,
            full_name=patient.doctor.full_name,
            specialization=patient.doctor.specialization,
            phone=patient.doctor.phone,
            clinic_name=patient.doctor.clinic_name,
            clinic_address=patient.doctor.clinic_address,
        ),
    )


@router.get(
    "/{patient_id}",
    response_model=PatientQuickRegisterResponse,
    summary="Get onsite patient details",
    description="Retrieve a patient's full record for edit/review during onsite consultation.",
)
def get_onsite_patient(
    patient_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientQuickRegisterResponse:
    """Get a single patient's record."""

    patient = session.get(Patient, patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found.",
        )

    if patient.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own patients.",
        )

    is_temp_cnic = patient.cnic.startswith("TEMP-")

    return PatientQuickRegisterResponse(
        id=patient.id,
        full_name=patient.full_name,
        phone=patient.phone,
        gender=patient.gender,
        cnic=patient.cnic,
        is_temp_cnic=is_temp_cnic,
        created_date=patient.created_date,
        last_visit_date=patient.last_visit_date,
        is_active=patient.is_active,
        age=_calculate_age(patient.date_of_birth),
        date_of_birth=patient.date_of_birth,
        email=patient.email,
        phone_secondary=patient.phone_secondary,
        residential_address=patient.residential_address,
        city=patient.city,
        occupation=patient.occupation,
        referred_by=patient.referred_by,
        medical_history=patient.medical_history,
        drug_allergies=patient.drug_allergies,
        family_history=patient.family_history,
        current_medications=patient.current_medications,
        notes=patient.notes,
        payment_status=patient.payment_status,
        doctor=DoctorBasicInfo(
            id=patient.doctor.id,
            full_name=patient.doctor.full_name,
            specialization=patient.doctor.specialization,
            phone=patient.doctor.phone,
            clinic_name=patient.doctor.clinic_name,
            clinic_address=patient.doctor.clinic_address,
        ),
    )
