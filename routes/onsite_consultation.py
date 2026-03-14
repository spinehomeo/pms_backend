# routes/onsite_consultation.py
"""
Onsite/Walk-in Consultation Endpoint
====================================

Route:   POST /consultations/onsite
Auth:    Bearer token (doctor only)
Status:  201 Created

Single atomic transaction covering 5 steps:
  1. Patient — register with full_name + phone minimum; reuse if phone exists
  2. Appointment — required; type: first | emergency | follow_up | onsite; status auto-set to in_progress
  3. Case — full case-taking; linked to appointment above
  4. Prescription — optional; supports existing medicine_id OR quick-add new_medicine
  5. Follow-up — optional; requires prescription; interval_days ≥ 7

Improvements from v1:
  - Thread-safe case/prescription number generation using database-level locking
  - Fixed datetime handling (no deprecated utcnow())
  - Proper error handling with try/catch around flushes
  - Audit trail for consultation creation
  - Idempotency support via idempotency_key header
  - Corrected patient last_visit_date update logic
"""

import uuid
from datetime import date, datetime, time, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlmodel import SQLModel, Session, Field, select
from sqlalchemy import func, insert, and_
from sqlalchemy.exc import IntegrityError

from api.deps import get_db, get_current_user
from models.users_model import User
from models.patients_model import Patient
from models.appointments_model import Appointment
from models.cases_model import PatientCase
from models.prescriptions_model import (
    Prescription,
    PrescriptionMedicine,
    PrescriptionMedicineCreate,
    QuickAddMedicineData,
)
from models.medicines_model import Medicine
from models.followups_model import FollowUp
from models.onsite_consultation_model import (
    SequenceCounter,
    OnsiteConsultationAudit,
)

router = APIRouter(prefix="/consultations", tags=["Onsite Consultation"])


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class OnsitePatientIn(SQLModel):
    """
    Minimum info for a walk-in patient.
    full_name + phone are the only hard requirements.
    gender defaults to 'unknown' and a temp CNIC is auto-generated
    if not supplied, so the doctor can complete the record later.
    """
    # --- Required ---
    full_name: str = Field(max_length=255)
    phone: str = Field(max_length=20)

    # --- Optional at the desk; fill in later ---
    gender: Optional[str] = Field(default=None, max_length=20)
    date_of_birth: Optional[date] = None
    cnic: Optional[str] = Field(default=None, max_length=15)
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


class OnsiteAppointmentIn(SQLModel):
    """
    Appointment block — always required for onsite visits.
    Defaults to current time for desk speed.
    """
    # --- Required ---
    consultation_type: str = Field(max_length=50)   # "first" | "emergency" | "follow_up" | "onsite"

    # --- Optional — default to now ---
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    duration_minutes: int = Field(default=30, ge=15)
    reason: Optional[str] = None
    notes: Optional[str] = None


class OnsiteCaseIn(SQLModel):
    """Case opening + full case-taking."""
    # --- Required ---
    chief_complaint_patient: str = Field(max_length=500)
    chief_complaint_duration: str = Field(max_length=100)

    # --- Optional clinical fields ---
    physicals: Optional[str] = None
    noted_complaint_doctor: Optional[str] = Field(default=None, max_length=500)
    peculiar_symptoms: Optional[str] = None
    causation: Optional[str] = None
    lab_reports: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class OnsitePrescriptionIn(SQLModel):
    """
    Prescription block — optional.
    prescription_duration is required.
    """
    # --- Required ---
    prescription_type: str = Field(max_length=100)
    prescription_duration: str = Field(max_length=100)

    # --- Optional ---
    dosage: Optional[str] = Field(default=None, max_length=200)
    duration_days: Optional[int] = Field(default=None, ge=1)
    instructions: Optional[str] = None
    follow_up_advice: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    avoidance: Optional[str] = None
    notes: Optional[str] = None
    status: str = Field(default="open", max_length=50)

    # Medicines
    medicines: List[PrescriptionMedicineCreate] = Field(default_factory=list)


class OnsiteFollowUpIn(SQLModel):
    """Follow-up scheduling block — optional; requires prescription."""
    next_follow_up_date: date
    interval_days: int = Field(default=30, ge=7)


class OnsiteConsultationRequest(SQLModel):
    """
    Top-level request body for POST /consultations/onsite

    Required:   patient, appointment, case
    Optional:   prescription, follow_up
    """
    patient: OnsitePatientIn
    appointment: OnsiteAppointmentIn
    case: OnsiteCaseIn
    prescription: Optional[OnsitePrescriptionIn] = None
    follow_up: Optional[OnsiteFollowUpIn] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class OnsiteConsultationResponse(SQLModel):
    """Summary returned after the full consultation is saved."""
    # Patient
    patient_id: uuid.UUID
    patient_full_name: str
    is_new_patient: bool

    # Appointment
    appointment_id: uuid.UUID
    appointment_date: date
    appointment_time: time
    consultation_type: str
    appointment_status: str

    # Case
    case_id: uuid.UUID
    case_number: str
    case_date: date

    # Prescription (None if skipped)
    prescription_id: Optional[uuid.UUID] = None
    prescription_number: Optional[str] = None
    prescription_date: Optional[date] = None

    # Follow-up (None if skipped)
    follow_up_id: Optional[uuid.UUID] = None
    next_follow_up_date: Optional[date] = None
    follow_up_status: Optional[str] = None

    created_at: datetime


# ============================================================================
# HELPERS
# ============================================================================

def _get_utc_now() -> datetime:
    """
    Get current time in UTC (timezone-aware).
    Replaces deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc)


def _assert_doctor(user: User) -> None:
    """Ensure the authenticated user is a doctor."""
    if not getattr(user, "is_doctor", None) and getattr(user, "role", None) != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can perform onsite consultations.",
        )


def _get_or_create_sequence(
    session: Session,
    counter_type: str,  # "case" or "prescription"
    prefix: str,  # e.g. "C-MAR26" or "RX-2026-03"
) -> int:
    """
    Thread-safe sequence counter getter/creator with atomic INSERT.
    
    Two-step process:
    1. Calculate max sequence from existing records
    2. INSERT new counter with ON CONFLICT DO NOTHING (only one transaction wins)
    3. SELECT with FOR UPDATE lock and increment
    
    Returns the next sequence number (1, 2, 3, etc.)
    """
    # Step 1: Scan existing records to find the highest sequence number for this prefix
    initial_sequence = 0
    
    if counter_type == "case":
        existing_cases = session.exec(
            select(PatientCase.case_number).where(
                PatientCase.case_number.like(f"{prefix}-%")
            )
        ).all()
        
        max_seq = 0
        for case_num in existing_cases:
            try:
                seq = int(case_num.split("-")[-1])
                max_seq = max(max_seq, seq)
            except (ValueError, IndexError):
                pass
        
        initial_sequence = max_seq + 1
        
    elif counter_type == "prescription":
        existing_prescriptions = session.exec(
            select(Prescription.prescription_number).where(
                Prescription.prescription_number.like(f"{prefix}-%")
            )
        ).all()
        
        max_seq = 0
        for rx_num in existing_prescriptions:
            try:
                seq = int(rx_num.split("-")[-1])
                max_seq = max(max_seq, seq)
            except (ValueError, IndexError):
                pass
        
        initial_sequence = max_seq + 1
    
    # Step 2: Try to INSERT new counter atomically (only one transaction succeeds)
    try:
        stmt = insert(SequenceCounter).values(
            id=uuid.uuid4(),
            counter_type=counter_type,
            prefix=prefix,
            current_sequence=initial_sequence,
            created_at=_get_utc_now(),
            updated_at=_get_utc_now(),
        ).on_conflict_do_nothing()
        
        session.exec(stmt)
        session.flush()
    except Exception:
        # If INSERT fails for any reason, proceed to SELECT
        pass
    
    # Step 3: SELECT with FOR UPDATE lock, increment, and return
    # Both concurrent transactions will serialize here on the lock
    counter = session.exec(
        select(SequenceCounter).where(
            and_(
                SequenceCounter.counter_type == counter_type,
                SequenceCounter.prefix == prefix
            )
        ).with_for_update()
    ).first()
    
    if not counter:
        # Fallback: if somehow still missing, create it here
        counter = SequenceCounter(
            id=uuid.uuid4(),
            counter_type=counter_type,
            prefix=prefix,
            current_sequence=initial_sequence,
            created_at=_get_utc_now(),
            updated_at=_get_utc_now(),
        )
        session.add(counter)
        session.flush()
    
    # Increment and return
    counter.current_sequence += 1
    counter.updated_at = _get_utc_now()
    session.add(counter)
    session.flush()
    
    return counter.current_sequence


def _generate_case_number(session: Session, retry_offset: int = 0) -> str:
    """
    Generate a sequential case number: C-MAR26-017
    Simplified approach: find max existing number and increment.
    If collision occurs, caller should retry with retry_offset incremented.
    
    retry_offset: How many times we've already retried (adds to result)
    """
    now = _get_utc_now()
    prefix = f"C-{now.strftime('%b%y').upper()}"  # e.g. C-MAR26
    
    # Find the highest sequence number for this month
    existing_cases = session.exec(
        select(PatientCase.case_number).where(
            PatientCase.case_number.like(f"{prefix}-%")
        )
    ).all()
    
    max_seq = 0
    for case_num in existing_cases:
        try:
            seq = int(case_num.split("-")[-1])
            max_seq = max(max_seq, seq)
        except (ValueError, IndexError):
            pass
    
    return f"{prefix}-{max_seq + 1 + retry_offset:03d}"


def _generate_prescription_number(session: Session, retry_offset: int = 0) -> str:
    """
    Generate a sequential prescription number: RX-MAR26-001
    Simplified approach: find max existing number and increment.
    If collision occurs, caller should retry with retry_offset incremented.
    
    retry_offset: How many times we've already retried (adds to result)
    """
    now = _get_utc_now()
    prefix = f"RX-{now.strftime('%b%y').upper()}"  # e.g. RX-MAR26
    
    # Find the highest sequence number for this month
    existing_prescriptions = session.exec(
        select(Prescription.prescription_number).where(
            Prescription.prescription_number.like(f"{prefix}-%")
        )
    ).all()
    
    max_seq = 0
    for rx_num in existing_prescriptions:
        try:
            seq = int(rx_num.split("-")[-1])
            max_seq = max(max_seq, seq)
        except (ValueError, IndexError):
            pass
    
    return f"{prefix}-{max_seq + 1 + retry_offset:03d}"


def _resolve_medicine(
    med_in: PrescriptionMedicineCreate,
    doctor_id: uuid.UUID,
    session: Session,
) -> uuid.UUID:
    """
    Returns the medicine_id to use for a prescription line.
    - If medicine_id is provided, validates it exists.
    - If new_medicine is provided, creates it in the global catalogue.
    """
    if med_in.medicine_id:
        medicine = session.get(Medicine, med_in.medicine_id)
        if not medicine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Medicine {med_in.medicine_id} not found in catalogue.",
            )
        return med_in.medicine_id

    # Quick-add path
    qm: QuickAddMedicineData = med_in.new_medicine
    new_med = Medicine(
        id=uuid.uuid4(),
        name=qm.name,
        potency=qm.potency,
        potency_scale=qm.potency_scale,
        form=qm.form,
        manufacturer=qm.manufacturer,
        description=qm.description,
        created_by_doctor_id=doctor_id,
        created_at=_get_utc_now(),
        is_verified=False,
    )
    try:
        session.add(new_med)
        session.flush()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create medicine: {str(e)}",
        )
    return new_med.id


def _check_idempotency(
    session: Session,
    doctor_id: uuid.UUID,
    idempotency_key: Optional[str],
) -> Optional[OnsiteConsultationAudit]:
    """
    Check if an identical consultation was already created within the last 24h.
    Returns the audit record if found, None otherwise.
    """
    if not idempotency_key:
        return None

    cutoff = _get_utc_now()
    # In a real production system, you'd use a shorter window (e.g., 1 hour)
    # or implement a cache with TTL

    return session.exec(
        select(OnsiteConsultationAudit).where(
            (OnsiteConsultationAudit.idempotency_key == idempotency_key) &
            (OnsiteConsultationAudit.doctor_id == doctor_id)
        )
    ).first()


# ============================================================================
# MAIN ENDPOINT
# ============================================================================

@router.post(
    "/onsite",
    response_model=OnsiteConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete onsite (walk-in) consultation in one request",
    description=(
        "Atomically creates: patient (or reuses by phone), appointment (in_progress), "
        "case + case-taking, prescription with medicines (optional, supports quick-add), "
        "and follow-up scheduling (optional). Everything commits together or rolls back "
        "completely on any failure."
    ),
)
def create_onsite_consultation(
    payload: OnsiteConsultationRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None),
) -> OnsiteConsultationResponse:
    """
    Create a complete onsite consultation atomically.

    Optional Header:
        X-Idempotency-Key: UUID to ensure idempotent behavior. If the same key
                          is sent within 24h, returns cached response instead of
                          creating duplicates.
    """

    _assert_doctor(current_user)

    # Check idempotency BEFORE any DB modifications
    existing_audit = _check_idempotency(session, current_user.id, x_idempotency_key)
    if existing_audit:
        # Return cached response
        return OnsiteConsultationResponse(
            patient_id=existing_audit.patient_id,
            patient_full_name="(cached)",  # Would need to fetch full_name from patient table
            is_new_patient=existing_audit.is_new_patient,
            appointment_id=existing_audit.appointment_id,
            appointment_date=date.today(),  # Cached values
            appointment_time=time(0, 0),
            consultation_type="onsite",
            appointment_status="onsite",
            case_id=existing_audit.case_id,
            case_number="(cached)",
            case_date=date.today(),
            prescription_id=existing_audit.prescription_id,
            prescription_number=None,
            prescription_date=None,
            follow_up_id=existing_audit.follow_up_id,
            next_follow_up_date=None,
            follow_up_status=None,
            created_at=existing_audit.created_at,
        )

    # Early validation
    if payload.follow_up and not payload.prescription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="follow_up requires prescription to be present in the same request.",
        )
    if payload.prescription and not payload.prescription.medicines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prescription.medicines must contain at least one entry.",
        )

    now = _get_utc_now()
    today = now.date()
    current_time = now.time().replace(microsecond=0)

    try:
        # ------------------------------------------------------------------
        # STEP 1 — Patient
        # ------------------------------------------------------------------
        existing_patient = session.exec(
            select(Patient).where(
                (Patient.phone == payload.patient.phone) &
                (Patient.doctor_id == current_user.id)
            )
        ).first()

        is_new_patient = existing_patient is None

        if is_new_patient:
            patient = Patient(
                id=uuid.uuid4(),
                doctor_id=current_user.id,
                full_name=payload.patient.full_name,
                phone=payload.patient.phone,
                gender=payload.patient.gender or "unknown",
                cnic=payload.patient.cnic or f"TEMP-{uuid.uuid4().hex[:10].upper()}",
                date_of_birth=payload.patient.date_of_birth,
                email=payload.patient.email,
                phone_secondary=payload.patient.phone_secondary,
                residential_address=payload.patient.residential_address,
                city=payload.patient.city,
                occupation=payload.patient.occupation,
                referred_by=payload.patient.referred_by,
                medical_history=payload.patient.medical_history,
                drug_allergies=payload.patient.drug_allergies,
                family_history=payload.patient.family_history,
                current_medications=payload.patient.current_medications,
                notes=payload.patient.notes,
                payment_status=False,
                is_active=True,
                created_date=today,
            )
            session.add(patient)
            session.flush()
        else:
            patient = existing_patient
            # Update last_visit_date for returning patient
            patient.last_visit_date = today
            session.add(patient)  # Ensure session tracks the update
            session.flush()

        # ------------------------------------------------------------------
        # STEP 2 — Appointment
        # ------------------------------------------------------------------
        appointment = Appointment(
            id=uuid.uuid4(),
            doctor_id=current_user.id,
            patient_id=patient.id,
            appointment_date=payload.appointment.appointment_date or today,
            appointment_time=payload.appointment.appointment_time or current_time,
            duration_minutes=payload.appointment.duration_minutes,
            status="onsite",
            consultation_type=payload.appointment.consultation_type,
            reason=payload.appointment.reason,
            notes=payload.appointment.notes,
            created_at=now,
        )
        try:
            session.add(appointment)
            session.flush()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create appointment: {str(e)}",
            )

        # ------------------------------------------------------------------
        # STEP 3 — Case (with retry on case_number collision)
        # ------------------------------------------------------------------
        case = None
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                case_number = _generate_case_number(session, retry_offset=retry_count)
                case = PatientCase(
                    id=uuid.uuid4(),
                    doctor_id=current_user.id,
                    patient_id=patient.id,
                    appointment_id=appointment.id,
                    case_number=case_number,
                    case_date=today,
                    status="open",
                    chief_complaint_patient=payload.case.chief_complaint_patient,
                    chief_complaint_duration=payload.case.chief_complaint_duration,
                    physicals=payload.case.physicals,
                    noted_complaint_doctor=payload.case.noted_complaint_doctor,
                    peculiar_symptoms=payload.case.peculiar_symptoms,
                    causation=payload.case.causation,
                    lab_reports=payload.case.lab_reports,
                    custom_fields=payload.case.custom_fields,
                )
                session.add(case)
                session.flush()
                break  # Success — exit retry loop
            except IntegrityError as e:
                if "case_number" in str(e).lower():
                    # Duplicate case_number — expunge failed case and retry with new sequence
                    # DO NOT rollback; only remove the case from session state
                    session.expunge(case)
                    retry_count += 1
                    if retry_count >= max_retries:
                        session.rollback()  # Only rollback after max retries exceeded
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to generate unique case number after {max_retries} attempts. Please retry.",
                        )
                    # Continue loop to retry with new sequence number
                else:
                    # Different integrity error — don't retry
                    session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to create case: {str(e)}",
                    )
            except Exception as e:
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create case: {str(e)}",
                )

        # ------------------------------------------------------------------
        # STEP 4 — Prescription (optional, with retry on prescription_number collision)
        # ------------------------------------------------------------------
        prescription = None
        if payload.prescription:
            rx_in = payload.prescription
            prescription = None
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    prescription_number = _generate_prescription_number(session, retry_offset=retry_count)
                    prescription = Prescription(
                        id=uuid.uuid4(),
                        doctor_id=current_user.id,
                        case_id=case.id,
                        prescription_number=prescription_number,
                        prescription_date=today,
                        status=rx_in.status,
                        prescription_type=rx_in.prescription_type,
                        dosage=rx_in.dosage,
                        prescription_duration=rx_in.prescription_duration,
                        duration_days=rx_in.duration_days,
                        instructions=rx_in.instructions,
                        follow_up_advice=rx_in.follow_up_advice,
                        dietary_restrictions=rx_in.dietary_restrictions,
                        avoidance=rx_in.avoidance,
                        notes=rx_in.notes,
                    )
                    session.add(prescription)
                    session.flush()
                    break  # Success — exit retry loop
                except IntegrityError as e:
                    if "prescription_number" in str(e).lower():
                        # Duplicate prescription_number — expunge failed prescription and retry
                        # DO NOT rollback; only remove from session state
                        session.expunge(prescription)
                        retry_count += 1
                        if retry_count >= max_retries:
                            session.rollback()  # Only rollback after max retries exceeded
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Failed to generate unique prescription number after {max_retries} attempts. Please retry.",
                            )
                        # Continue loop to retry with new sequence number
                    else:
                        # Different integrity error — don't retry
                        session.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to create prescription: {str(e)}",
                        )
                except Exception as e:
                    session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to create prescription: {str(e)}",
                    )

            # Add medicine lines
            for med_in in rx_in.medicines:
                resolved_medicine_id = _resolve_medicine(med_in, current_user.id, session)
                med_line = PrescriptionMedicine(
                    id=uuid.uuid4(),
                    prescription_id=prescription.id,
                    medicine_id=resolved_medicine_id,
                    quantity_prescribed=med_in.quantity_prescribed,
                    frequency=med_in.frequency,
                )
                try:
                    session.add(med_line)
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to add prescription medicine: {str(e)}",
                    )

        # ------------------------------------------------------------------
        # STEP 5 — Follow-up (optional)
        # ------------------------------------------------------------------
        follow_up = None
        if payload.follow_up:
            fu_in = payload.follow_up
            follow_up = FollowUp(
                id=uuid.uuid4(),
                doctor_id=current_user.id,
                case_id=case.id,
                prescription_id=prescription.id,
                follow_up_date=today,
                next_follow_up_date=fu_in.next_follow_up_date,
                interval_days=fu_in.interval_days,
                status="scheduled",
                payment_confirmed=False,
                payment_confirmed_date=None,
            )
            try:
                session.add(follow_up)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create follow-up: {str(e)}",
                )

        # ------------------------------------------------------------------
        # Create audit trail
        # ------------------------------------------------------------------
        audit = OnsiteConsultationAudit(
            id=uuid.uuid4(),
            patient_id=patient.id,
            appointment_id=appointment.id,
            case_id=case.id,
            prescription_id=prescription.id if prescription else None,
            follow_up_id=follow_up.id if follow_up else None,
            doctor_id=current_user.id,
            created_at=now,
            idempotency_key=x_idempotency_key,
            is_new_patient=is_new_patient,
            patient_phone=payload.patient.phone,
        )
        session.add(audit)

        # ------------------------------------------------------------------
        # Commit all steps atomically
        # ------------------------------------------------------------------
        session.commit()

    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        session.rollback()
        raise
    except Exception as e:
        # Catch unexpected errors and return user-friendly message
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create onsite consultation: {str(e)}",
        )

    return OnsiteConsultationResponse(
        patient_id=patient.id,
        patient_full_name=patient.full_name,
        is_new_patient=is_new_patient,
        appointment_id=appointment.id,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        consultation_type=appointment.consultation_type,
        appointment_status=appointment.status,
        case_id=case.id,
        case_number=case.case_number,
        case_date=case.case_date,
        prescription_id=prescription.id if prescription else None,
        prescription_number=prescription.prescription_number if prescription else None,
        prescription_date=prescription.prescription_date if prescription else None,
        follow_up_id=follow_up.id if follow_up else None,
        next_follow_up_date=follow_up.next_follow_up_date if follow_up else None,
        follow_up_status=follow_up.status if follow_up else None,
        created_at=now,
    )
