"""
Onsite Consultation Endpoint
==============================
Route:   POST /consultations/onsite
Auth:    Bearer token (doctor only)

Single atomic transaction covering 5 steps:
  1. Patient  — register with full_name + phone minimum; reuse if phone exists
  2. Appointment — required; type: first | emergency | follow_up | onsite; status auto-set to in_progress
  3. Case     — full case-taking; linked to appointment above
  4. Prescription — optional; supports existing medicine_id OR quick-add new_medicine
  5. Follow-up — optional; requires prescription; interval_days ge=7

Field names and types match your actual DB models exactly.
"""

import uuid
from datetime import date, datetime, time
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel, Session, Field, select, Column
from sqlalchemy.dialects.postgresql import JSONB

from app.api.deps import get_db, get_current_user
from app.models.users_model import User
from app.models.patients_model import Patient
from app.models.appointments_model import Appointment
from app.models.cases_model import PatientCase
from app.models.prescriptions_model import (
    Prescription,
    PrescriptionMedicine,
    PrescriptionMedicineCreate,   # reused directly — already validates medicine_id XOR new_medicine
    QuickAddMedicineData,
)
from app.models.medicines_model import Medicine
from app.models.followups_model import FollowUp

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
    gender: Optional[str] = Field(default=None, max_length=20)         # defaults to "unknown" if omitted
    date_of_birth: Optional[date] = None
    cnic: Optional[str] = Field(default=None, max_length=15)           # auto-generated temp if omitted
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
    appointment_date and appointment_time default to right now
    so the doctor doesn't have to type them.
    consultation_type MUST be provided explicitly.
    """
    # --- Required ---
    consultation_type: str = Field(max_length=50)   # "first" | "emergency" | "follow_up" | "onsite"

    # --- Optional — default to now ---
    appointment_date: Optional[date] = None         # defaults to today
    appointment_time: Optional[time] = None         # defaults to current time
    duration_minutes: int = Field(default=30, ge=15)
    reason: Optional[str] = None
    notes: Optional[str] = None


class OnsiteCaseIn(SQLModel):
    """
    Case opening + full case-taking.
    Field names match PatientCaseBase exactly.
    """
    # --- Required ---
    chief_complaint_patient: str = Field(max_length=500)    # patient's own words
    chief_complaint_duration: str = Field(max_length=100)   # e.g. "3 days", "2 weeks"

    # --- Optional clinical fields ---
    physicals: Optional[str] = None                         # physical examination findings
    noted_complaint_doctor: Optional[str] = Field(default=None, max_length=500)  # doctor's assessment
    peculiar_symptoms: Optional[str] = None
    causation: Optional[str] = None
    lab_reports: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None          # dynamic JSONB fields


class OnsitePrescriptionIn(SQLModel):
    """
    Prescription block — optional.
    dosage and prescription_duration are required by PrescriptionBase,
    so they are required here too.
    medicines reuses PrescriptionMedicineCreate directly, which already
    validates medicine_id XOR new_medicine per entry.
    """
    # --- Required (match PrescriptionBase) ---
    prescription_type: str = Field(max_length=100)          # e.g. "constitutional", "acute"
    dosage: str = Field(max_length=200)                     # e.g. "3 times daily"
    prescription_duration: str = Field(max_length=100)      # e.g. "14 days"

    # --- Optional ---
    duration_days: Optional[int] = Field(default=None, ge=1)  # integer version for auto follow-up date calc
    instructions: Optional[str] = None
    follow_up_advice: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    avoidance: Optional[str] = None                         # lifestyle avoidance
    notes: Optional[str] = None
    status: str = Field(default="open", max_length=50)      # open | completed | cancelled

    # Medicines — reuses existing model with its built-in validation
    medicines: List[PrescriptionMedicineCreate] = Field(default_factory=list)


class OnsiteFollowUpIn(SQLModel):
    """
    Follow-up scheduling block — optional; requires prescription.
    interval_days ge=7 matches the FollowUp DB model constraint.
    next_follow_up_date: the date the patient should return.
    """
    next_follow_up_date: date                               # the date doctor sets for next visit
    interval_days: int = Field(default=30, ge=7)            # number of days between visits


class OnsiteConsultationRequest(SQLModel):
    """
    Top-level request body for POST /consultations/onsite

    Required:   patient, appointment, case
    Optional:   prescription, follow_up

    Rules:
      - follow_up requires prescription to be present
      - prescription.medicines must be non-empty if prescription is included
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
    """
    Summary returned after the full consultation is saved.
    All IDs and numbers needed for the frontend to navigate to
    each created record.
    """
    # Patient
    patient_id: uuid.UUID
    patient_full_name: str
    is_new_patient: bool                        # False if existing patient was matched by phone

    # Appointment
    appointment_id: uuid.UUID
    appointment_date: date
    appointment_time: time
    consultation_type: str
    appointment_status: str                     # always "in_progress"

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

def _assert_doctor(user: User) -> None:
    """Ensure the authenticated user is a doctor."""
    if not getattr(user, "is_doctor", None) and getattr(user, "role", None) != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can perform onsite consultations.",
        )


def _generate_case_number(session: Session) -> str:
    """
    Generate a sequential case number matching the existing pattern: C-MAR26-017
    Scoped per month so sequence resets each month.
    """
    now = datetime.utcnow()
    prefix = f"C-{now.strftime('%b%y').upper()}"   # e.g. C-MAR26
    existing = session.exec(
        select(PatientCase)
        .where(PatientCase.case_number.startswith(prefix))
        .order_by(PatientCase.case_number.desc())
    ).first()
    seq = (int(existing.case_number.rsplit("-", 1)[-1]) + 1) if existing else 1
    return f"{prefix}-{seq:03d}"


def _generate_prescription_number(session: Session) -> str:
    """
    Generate a sequential prescription number: RX-2026-03-005
    Scoped per month.
    """
    now = datetime.utcnow()
    prefix = f"RX-{now.year}-{now.month:02d}"
    existing = session.exec(
        select(Prescription)
        .where(Prescription.prescription_number.startswith(prefix))
        .order_by(Prescription.prescription_number.desc())
    ).first()
    seq = (int(existing.prescription_number.rsplit("-", 1)[-1]) + 1) if existing else 1
    return f"{prefix}-{seq:03d}"


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
        created_at=datetime.utcnow(),
        is_verified=False,          # admin verifies later
    )
    session.add(new_med)
    session.flush()
    return new_med.id


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
) -> OnsiteConsultationResponse:

    _assert_doctor(current_user)

    # Early validation — catch rule violations before hitting the DB
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

    now = datetime.utcnow()
    today = now.date()
    current_time = now.time().replace(microsecond=0)

    # ------------------------------------------------------------------
    # STEP 1 — Patient
    #   Match on phone number scoped to this doctor.
    #   If not found, register a new patient with minimum required fields.
    # ------------------------------------------------------------------
    existing_patient = session.exec(
        select(Patient).where(
            Patient.phone == payload.patient.phone,
            Patient.doctor_id == current_user.id,
        )
    ).first()

    is_new_patient = existing_patient is None

    if is_new_patient:
        patient = Patient(
            id=uuid.uuid4(),
            doctor_id=current_user.id,
            # Required fields — with safe defaults for walk-in speed
            full_name=payload.patient.full_name,
            phone=payload.patient.phone,
            gender=payload.patient.gender or "unknown",
            cnic=payload.patient.cnic or f"TEMP-{uuid.uuid4().hex[:10].upper()}",  # temp; update later
            # Optional fields
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
            payment_status=False,               # bool: False = unpaid
            is_active=True,
            created_date=today,
        )
        session.add(patient)
        session.flush()                         # resolve patient.id before next step
    else:
        patient = existing_patient
        # Update last visit date for returning patient
        patient.last_visit_date = today

    # ------------------------------------------------------------------
    # STEP 2 — Appointment
    #   Status is always "in_progress" — patient is present right now.
    #   Date/time default to now so the desk staff doesn't need to type them.
    # ------------------------------------------------------------------
    appointment = Appointment(
        id=uuid.uuid4(),
        doctor_id=current_user.id,
        patient_id=patient.id,
        appointment_date=payload.appointment.appointment_date or today,
        appointment_time=payload.appointment.appointment_time or current_time,
        duration_minutes=payload.appointment.duration_minutes,
        status="in_progress",                   # locked for onsite — patient is here
        consultation_type=payload.appointment.consultation_type,
        reason=payload.appointment.reason,
        notes=payload.appointment.notes,
        created_at=now,
    )
    session.add(appointment)
    session.flush()                             # resolve appointment.id before next step

    # ------------------------------------------------------------------
    # STEP 3 — Case + case-taking
    #   Linked to the appointment created above.
    #   Field names match PatientCaseBase exactly.
    # ------------------------------------------------------------------
    case_number = _generate_case_number(session)

    case = PatientCase(
        id=uuid.uuid4(),
        doctor_id=current_user.id,
        patient_id=patient.id,
        appointment_id=appointment.id,          # linked to the walk-in appointment
        case_number=case_number,
        case_date=today,
        status="open",
        # Required case fields
        chief_complaint_patient=payload.case.chief_complaint_patient,
        chief_complaint_duration=payload.case.chief_complaint_duration,
        # Optional clinical fields — exact names from PatientCaseBase
        physicals=payload.case.physicals,
        noted_complaint_doctor=payload.case.noted_complaint_doctor,
        peculiar_symptoms=payload.case.peculiar_symptoms,
        causation=payload.case.causation,
        lab_reports=payload.case.lab_reports,
        custom_fields=payload.case.custom_fields,
    )
    session.add(case)
    session.flush()                             # resolve case.id before next step

    # ------------------------------------------------------------------
    # STEP 4 — Prescription (optional)
    #   Supports both existing medicine_id and quick-add new_medicine
    #   per the existing PrescriptionMedicineCreate contract.
    # ------------------------------------------------------------------
    prescription = None
    if payload.prescription:
        rx_in = payload.prescription
        prescription_number = _generate_prescription_number(session)

        prescription = Prescription(
            id=uuid.uuid4(),
            doctor_id=current_user.id,
            case_id=case.id,
            prescription_number=prescription_number,
            prescription_date=today,
            status=rx_in.status,
            # Required PrescriptionBase fields
            prescription_type=rx_in.prescription_type,
            dosage=rx_in.dosage,
            prescription_duration=rx_in.prescription_duration,
            # Optional PrescriptionBase fields
            duration_days=rx_in.duration_days,
            instructions=rx_in.instructions,
            follow_up_advice=rx_in.follow_up_advice,
            dietary_restrictions=rx_in.dietary_restrictions,
            avoidance=rx_in.avoidance,
            notes=rx_in.notes,
        )
        session.add(prescription)
        session.flush()                         # resolve prescription.id before medicines

        # Add medicine lines — resolve medicine_id for each entry
        for med_in in rx_in.medicines:
            resolved_medicine_id = _resolve_medicine(med_in, current_user.id, session)
            med_line = PrescriptionMedicine(
                id=uuid.uuid4(),
                prescription_id=prescription.id,
                medicine_id=resolved_medicine_id,
                quantity_prescribed=med_in.quantity_prescribed,
                frequency=med_in.frequency,
            )
            session.add(med_line)

    # ------------------------------------------------------------------
    # STEP 5 — Follow-up (optional; requires prescription)
    #   next_follow_up_date: the date the patient should return.
    #   follow_up_date: today (when this follow-up was scheduled).
    #   interval_days ge=7 enforced by OnsiteFollowUpIn.
    # ------------------------------------------------------------------
    follow_up = None
    if payload.follow_up:
        fu_in = payload.follow_up
        follow_up = FollowUp(
            id=uuid.uuid4(),
            doctor_id=current_user.id,
            case_id=case.id,
            prescription_id=prescription.id,
            follow_up_date=today,               # date this follow-up record was created
            next_follow_up_date=fu_in.next_follow_up_date,  # date patient should return
            interval_days=fu_in.interval_days,
            status="scheduled",                 # default per FollowupStatus workflow
            payment_confirmed=False,
            payment_confirmed_date=None,
        )
        session.add(follow_up)

    # ------------------------------------------------------------------
    # Commit all 5 steps atomically
    # ------------------------------------------------------------------
    session.commit()

    return OnsiteConsultationResponse(
        # Patient
        patient_id=patient.id,
        patient_full_name=patient.full_name,
        is_new_patient=is_new_patient,
        # Appointment
        appointment_id=appointment.id,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        consultation_type=appointment.consultation_type,
        appointment_status=appointment.status,
        # Case
        case_id=case.id,
        case_number=case.case_number,
        case_date=case.case_date,
        # Prescription
        prescription_id=prescription.id if prescription else None,
        prescription_number=prescription.prescription_number if prescription else None,
        prescription_date=prescription.prescription_date if prescription else None,
        # Follow-up
        follow_up_id=follow_up.id if follow_up else None,
        next_follow_up_date=follow_up.next_follow_up_date if follow_up else None,
        follow_up_status=follow_up.status if follow_up else None,
        created_at=now,
    )


# ============================================================================
# EXAMPLE REQUEST PAYLOADS (for Swagger / frontend reference)
# ============================================================================
#
# ── Minimal (patient + appointment + case only) ──────────────────────────────
# POST /consultations/onsite
# {
#   "patient": {
#     "full_name": "Ali Hassan",
#     "phone": "03001234567"
#   },
#   "appointment": {
#     "consultation_type": "first"
#   },
#   "case": {
#     "chief_complaint_patient": "Severe headache since 3 days",
#     "chief_complaint_duration": "3 days"
#   }
# }
#
# ── Full (all 5 steps) ───────────────────────────────────────────────────────
# POST /consultations/onsite
# {
#   "patient": {
#     "full_name": "Ali Hassan",
#     "phone": "03001234567",
#     "gender": "male",
#     "city": "Karachi",
#     "cnic": "42101-1234567-1"
#   },
#   "appointment": {
#     "consultation_type": "first",
#     "duration_minutes": 45,
#     "reason": "Headache and fatigue"
#   },
#   "case": {
#     "chief_complaint_patient": "Severe headache since 3 days",
#     "chief_complaint_duration": "3 days",
#     "physicals": "BP 130/85, Pulse 78",
#     "noted_complaint_doctor": "Tension-type headache",
#     "peculiar_symptoms": "Worse in mornings",
#     "causation": "Stress and poor sleep"
#   },
#   "prescription": {
#     "prescription_type": "constitutional",
#     "dosage": "3 times daily",
#     "prescription_duration": "14 days",
#     "duration_days": 14,
#     "dietary_restrictions": "Avoid coffee",
#     "avoidance": "Avoid loud environments",
#     "medicines": [
#       {
#         "medicine_id": "a1b2c3d4-e5f6-...",   ← existing medicine from catalogue
#         "quantity_prescribed": "10 drops",
#         "frequency": "TDS"
#       },
#       {
#         "new_medicine": {                       ← quick-add, no catalogue lookup needed
#           "name": "Belladonna",
#           "potency": "30",
#           "potency_scale": "C",
#           "form": "Globules"
#         },
#         "quantity_prescribed": "5 drops",
#         "frequency": "BD"
#       }
#     ]
#   },
#   "follow_up": {
#     "next_follow_up_date": "2026-03-19",
#     "interval_days": 14
#   }
# }
#
# ── Example response ─────────────────────────────────────────────────────────
# {
#   "patient_id": "uuid...",
#   "patient_full_name": "Ali Hassan",
#   "is_new_patient": true,
#   "appointment_id": "uuid...",
#   "appointment_date": "2026-03-05",
#   "appointment_time": "14:32:00",
#   "consultation_type": "first",
#   "appointment_status": "in_progress",
#   "case_id": "uuid...",
#   "case_number": "C-MAR26-017",
#   "case_date": "2026-03-05",
#   "prescription_id": "uuid...",
#   "prescription_number": "RX-2026-03-005",
#   "prescription_date": "2026-03-05",
#   "follow_up_id": "uuid...",
#   "next_follow_up_date": "2026-03-19",
#   "follow_up_status": "scheduled",
#   "created_at": "2026-03-05T14:32:00"
# }
