# api/routes/prescriptions.py - WITH QUICK-ADD MEDICINE CAPABILITY + AUTO FOLLOW-UP SCHEDULING
import uuid
from typing import Any, List, Optional
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select, Session
from sqlalchemy.orm import selectinload
from sqlalchemy import insert, and_

from api.deps import CurrentUser, SessionDep
from models.prescriptions_model import (
    Prescription, PrescriptionCreate, PrescriptionPublic, PrescriptionsPublic,
    PrescriptionMedicine, PrescriptionMedicineCreate,
    PrescriptionUpdate,
    PrescriptionCreateResponse,                                  # NEW import
)
from models.followups_model import FollowUp                      # NEW import
from models.medicines_model import Medicine
from models.patients_model import Patient
from models.cases_model import PatientCase
from models.login_model import Message
from models.onsite_consultation_model import SequenceCounter, OnsiteConsultationAudit
from utils.enum_service import EnumService

router = APIRouter(prefix="/prescriptions", tags=["📋 Prescriptions"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_utc_now() -> datetime:
    """Get current time in UTC (timezone-aware). Replaces deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


def _get_or_create_sequence(
    session: Session,
    counter_type: str,
    prefix: str,
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
    
    if counter_type == "prescription":
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


def _generate_prescription_number(session: Session) -> str:
    """
    Generate a sequential prescription number: RX-MAR26-001
    Thread-safe: scoped per month using SequenceCounter table.
    Format: {TYPE}-{MONTH}{YEAR}-{SEQUENCE} e.g. RX-MAR26-002
    """
    now = _get_utc_now()
    prefix = f"RX-{now.strftime('%b%y').upper()}"  # e.g. RX-MAR26
    seq = _get_or_create_sequence(session, "prescription", prefix)
    return f"{prefix}-{seq:03d}"


@router.get("/", response_model=PrescriptionsPublic)
def read_prescriptions(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    case_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> Any:
    """
    Retrieve prescriptions with filtering options.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access prescriptions")
    
    count_statement = (
        select(func.count())
        .select_from(Prescription)
        .where(Prescription.doctor_id == current_user.id)
    )
    
    statement = (
        select(Prescription)
        .where(Prescription.doctor_id == current_user.id)
        .options(
            selectinload(Prescription.medicines).selectinload(PrescriptionMedicine.medicine),
            selectinload(Prescription.case).selectinload(PatientCase.patient)
        )
        .offset(skip)
        .limit(limit)
        .order_by(Prescription.prescription_date.desc())
    )
    
    if case_id:
        case = session.get(PatientCase, case_id)
        if not case or case.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Case not found")
        
        count_statement = count_statement.where(Prescription.case_id == case_id)
        statement = statement.where(Prescription.case_id == case_id)
    
    if from_date:
        count_statement = count_statement.where(Prescription.prescription_date >= from_date)
        statement = statement.where(Prescription.prescription_date >= from_date)
    
    if to_date:
        count_statement = count_statement.where(Prescription.prescription_date <= to_date)
        statement = statement.where(Prescription.prescription_date <= to_date)
    
    count = session.exec(count_statement).one()
    prescriptions = session.exec(statement).all()
    
    # Build response with patient_name, case_number, and medicines
    response_data = []
    for prescription in prescriptions:
        rx_data = prescription.model_dump(exclude={"medicines"})
        if prescription.case:
            rx_data['patient_name'] = prescription.case.patient.full_name if prescription.case.patient else None
            rx_data['case_number'] = prescription.case.case_number
        
        # Convert medicines to response format
        medicines_list = []
        for pm in prescription.medicines:
            medicine_dict = {
                "id": pm.id,
                "medicine_id": pm.medicine_id,
                "quantity_prescribed": pm.quantity_prescribed,
                "frequency": pm.frequency,
                "medicine": {
                    "id": pm.medicine.id,
                    "name": pm.medicine.name,
                    "potency": pm.medicine.potency,
                    "form": pm.medicine.form
                }
            }
            medicines_list.append(medicine_dict)
        
        rx_data['medicines'] = medicines_list
        response_data.append(PrescriptionPublic(**rx_data))
    
    return PrescriptionsPublic(data=response_data, count=count)


@router.get("/{prescription_id}", response_model=PrescriptionPublic)
def read_prescription(
    session: SessionDep,
    current_user: CurrentUser,
    prescription_id: uuid.UUID = Path(..., description="Prescription UUID")
) -> Any:
    """
    Get prescription by ID with medicines.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access prescriptions")
    
    statement = (
        select(Prescription)
        .where(Prescription.id == prescription_id)
        .options(
            selectinload(Prescription.medicines).selectinload(PrescriptionMedicine.medicine),
            selectinload(Prescription.case).selectinload(PatientCase.patient)
        )
    )
    prescription = session.exec(statement).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this prescription")
    
    # Build response with patient_name, case_number, and medicines
    rx_data = prescription.model_dump(exclude={"medicines"})
    if prescription.case:
        rx_data['patient_name'] = prescription.case.patient.full_name if prescription.case.patient else None
        rx_data['case_number'] = prescription.case.case_number
    
    # Convert medicines to response format
    medicines_list = []
    for pm in prescription.medicines:
        medicine_dict = {
            "id": pm.id,
            "medicine_id": pm.medicine_id,
            "quantity_prescribed": pm.quantity_prescribed,
            "frequency": pm.frequency,
            "medicine": {
                "id": pm.medicine.id,
                "name": pm.medicine.name,
                "potency": pm.medicine.potency,
                "form": pm.medicine.form
            }
        }
        medicines_list.append(medicine_dict)
    
    rx_data['medicines'] = medicines_list
    return PrescriptionPublic(**rx_data)


def _get_or_create_medicine(
    session,
    medicine_data: PrescriptionMedicineCreate,
    current_user_id: uuid.UUID
) -> uuid.UUID:
    """
    Helper function to get existing medicine or create new one.
    Used during prescription creation.
    """
    if medicine_data.medicine_id:
        # Medicine ID provided - verify it exists
        medicine = session.get(Medicine, medicine_data.medicine_id)
        if not medicine:
            raise HTTPException(
                status_code=404,
                detail=f"Medicine with ID {medicine_data.medicine_id} not found"
            )
        return medicine.id
    
    elif medicine_data.new_medicine:
        # New medicine data provided - check for duplicates first
        new_med = medicine_data.new_medicine
        
        existing = session.exec(
            select(Medicine)
            .where(
                Medicine.name == new_med.name,
                Medicine.potency == new_med.potency,
                Medicine.potency_scale == new_med.potency_scale,
                Medicine.form == new_med.form
            )
        ).first()
        
        if existing:
            # Found duplicate - use existing
            return existing.id
        
        # Create new medicine in global catalog
        medicine_data_dict = new_med.model_dump()
        medicine_data_dict["created_by_doctor_id"] = current_user_id
        medicine_data_dict["is_verified"] = False
        
        medicine = Medicine.model_validate(medicine_data_dict)
        session.add(medicine)
        session.flush()  # Get ID
        
        return medicine.id
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either medicine_id or new_medicine must be provided"
        )


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: resolve follow-up date from FollowUpSchedule + prescription context
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_followup_date(
    schedule,                        # FollowUpSchedule instance
    prescription_date: date,
    duration_days: Optional[int]
) -> date:
    """
    Priority order:
      1. Explicit date from doctor (schedule.follow_up_date)
      2. auto_calculate=True  → prescription_date + duration_days
      3. Fallback             → prescription_date + 30 days
    """
    if schedule.follow_up_date:
        return schedule.follow_up_date

    if schedule.auto_calculate and duration_days:
        return prescription_date + timedelta(days=duration_days)

    # Fallback: 30 days from prescription date
    return prescription_date + timedelta(days=30)


# ─────────────────────────────────────────────────────────────────────────────
# POST /prescriptions/
# CHANGED: response_model is now PrescriptionCreateResponse (was PrescriptionPublic)
# The prescription field inside it is identical to the old PrescriptionPublic,
# so existing clients that only read prescription data are unaffected.
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/", response_model=PrescriptionCreateResponse)  # CHANGED response_model
def create_prescription(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    prescription_in: PrescriptionCreate
) -> Any:
    """
    Create new prescription with medicines.

    Supports two ways to add medicines:
    1. Use existing medicine from catalog (provide medicine_id)
    2. Quick-add new medicine (provide new_medicine details)

    If medicine already exists in catalog, it will be reused instead of creating duplicate.

    **Auto follow-up scheduling (NEW):**
    Include an optional `follow_up_schedule` block to atomically create a scheduled
    follow-up alongside the prescription.  Three date modes are supported:

    - Explicit date:   `{ "follow_up_date": "2025-04-15" }`
    - Auto-calculate:  `{ "auto_calculate": true }` (requires `duration_days` on prescription)
    - Omit both:       backend defaults to prescription_date + 30 days

    If `follow_up_schedule` is omitted entirely, no follow-up is created (existing behaviour).
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create prescriptions")
    
    # Verify case belongs to doctor
    case = session.get(PatientCase, prescription_in.case_id)
    if not case or case.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Validate prescription type
    if not EnumService.validate_value(session, "PrescriptionType", prescription_in.prescription_type, current_user.id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid prescription type '{prescription_in.prescription_type}'. Use /enums/doctor/PrescriptionType to get valid options."
        )
    
    # Validate prescription status if provided
    if prescription_in.status:
        if not EnumService.validate_value(session, "PrescriptionStatus", prescription_in.status, current_user.id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid prescription status '{prescription_in.status}'. Use /enums/doctor/PrescriptionStatus to get valid options."
            )
    
    # Validate repetition intervals in medicines
    for medicine_in in prescription_in.medicines:
        if medicine_in.frequency:
            if not EnumService.validate_value(session, "RepetitionEnum", medicine_in.frequency, current_user.id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid frequency '{medicine_in.frequency}'. Use /enums/doctor/RepetitionEnum to get valid options."
                )
    
    # NEW: validate explicit follow-up date is in the future
    if prescription_in.follow_up_schedule and prescription_in.follow_up_schedule.follow_up_date:
        if prescription_in.follow_up_schedule.follow_up_date < date.today():
            raise HTTPException(
                status_code=400,
                detail="follow_up_schedule.follow_up_date must be today or a future date"
            )

    # Generate prescription number using thread-safe sequence counter
    prescription_number = _generate_prescription_number(session)
    
    # Create prescription (exclude follow_up_schedule — not a DB column)
    prescription_data = prescription_in.model_dump(exclude={"medicines", "follow_up_schedule"})  # CHANGED: added follow_up_schedule exclusion
    prescription_data.update({
        "doctor_id": current_user.id,
        "prescription_number": prescription_number
    })
    
    prescription = Prescription.model_validate(prescription_data)
    session.add(prescription)
    session.flush()  # Get prescription ID

    # Add medicines to prescription
    for medicine_in in prescription_in.medicines:
        # Get or create medicine
        medicine_id = _get_or_create_medicine(
            session, 
            medicine_in, 
            current_user.id
        )

        # Create prescription medicine relationship
        prescription_medicine = PrescriptionMedicine(
            prescription_id=prescription.id,
            medicine_id=medicine_id,
            quantity_prescribed=medicine_in.quantity_prescribed,
            frequency=medicine_in.frequency
        )
        session.add(prescription_medicine)

    # ─────────────────────────────────────────────────────────────────────────
    # NEW: Auto-create follow-up if follow_up_schedule was provided
    # This runs inside the same transaction — either both commit or both roll back.
    # ─────────────────────────────────────────────────────────────────────────
    created_followup_id: Optional[uuid.UUID] = None
    created_followup_date: Optional[date] = None

    if prescription_in.follow_up_schedule:
        schedule = prescription_in.follow_up_schedule

        # Resolve the target follow-up date
        fu_date = _resolve_followup_date(
            schedule,
            prescription.prescription_date,
            prescription_in.duration_days
        )

        # Calculate interval_days from the last follow-up on this case (or from prescription date)
        last_followup = session.exec(
            select(FollowUp)
            .where(FollowUp.case_id == prescription.case_id)
            .order_by(FollowUp.follow_up_date.desc())
        ).first()

        if last_followup:
            raw_interval = (fu_date - last_followup.follow_up_date).days
        else:
            raw_interval = (fu_date - prescription.prescription_date).days

        # Use explicit interval_days if doctor set one, otherwise use calculated value
        interval = schedule.interval_days if schedule.interval_days else max(raw_interval, 7)

        followup = FollowUp(
            case_id=prescription.case_id,
            prescription_id=prescription.id,
            doctor_id=current_user.id,
            follow_up_date=fu_date,
            interval_days=interval,
            status="scheduled",
            plan=schedule.notes,        # doctor's follow-up advice goes here
        )
        session.add(followup)
        session.flush()  # Get follow-up ID before commit

        created_followup_id = followup.id
        created_followup_date = fu_date

    # Single commit — prescription + medicines + optional follow-up
    session.commit()
    session.refresh(prescription)
    
    # Reload with eager loading of medicines and case
    statement = (
        select(Prescription)
        .where(Prescription.id == prescription.id)
        .options(
            selectinload(Prescription.medicines).selectinload(PrescriptionMedicine.medicine),
            selectinload(Prescription.case).selectinload(PatientCase.patient)
        )
    )
    prescription = session.exec(statement).one()
    
    # Build response with patient_name, case_number, and medicines
    rx_data = prescription.model_dump(exclude={"medicines"})
    if prescription.case:
        rx_data['patient_name'] = prescription.case.patient.full_name if prescription.case.patient else None
        rx_data['case_number'] = prescription.case.case_number
    
    # Convert medicines to response format
    medicines_list = []
    for pm in prescription.medicines:
        medicine_dict = {
            "id": pm.id,
            "medicine_id": pm.medicine_id,
            "quantity_prescribed": pm.quantity_prescribed,
            "frequency": pm.frequency,
            "medicine": {
                "id": pm.medicine.id,
                "name": pm.medicine.name,
                "potency": pm.medicine.potency,
                "form": pm.medicine.form
            }
        }
        medicines_list.append(medicine_dict)
    
    rx_data['medicines'] = medicines_list
    prescription_public = PrescriptionPublic(**rx_data)

    # Return combined response
    return PrescriptionCreateResponse(
        prescription=prescription_public,
        follow_up_scheduled=created_followup_id is not None,
        follow_up_id=created_followup_id,
        follow_up_date=created_followup_date,
    )


@router.put("/{prescription_id}", response_model=PrescriptionPublic)
def update_prescription(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    prescription_id: uuid.UUID,
    prescription_in: PrescriptionUpdate
) -> Any:
    """
    Update a prescription.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update prescriptions")
    
    prescription = session.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this prescription")
    
    # Update prescription details
    update_dict = prescription_in.model_dump(exclude={"medicines"}, exclude_unset=True)
    
    # Validate status if provided
    if update_dict.get("status"):
        if not EnumService.validate_value(session, "PrescriptionStatus", update_dict["status"], current_user.id):
            raise HTTPException(status_code=400, detail=f"Invalid prescription status: {update_dict['status']}")
    
    prescription.sqlmodel_update(update_dict)
    
    # If medicines are provided, update them
    if prescription_in.medicines is not None:
        # Delete old prescription medicines
        old_prescription_medicines = session.exec(
            select(PrescriptionMedicine)
            .where(PrescriptionMedicine.prescription_id == prescription_id)
        ).all()
        
        for old_pm in old_prescription_medicines:
            session.delete(old_pm)
        
        session.flush()
        
        # Add new medicines (supports quick-add)
        for medicine_in in prescription_in.medicines:
            medicine_id = _get_or_create_medicine(
                session,
                medicine_in,
                current_user.id
            )
            
            prescription_medicine = PrescriptionMedicine(
                prescription_id=prescription.id,
                medicine_id=medicine_id,
                quantity_prescribed=medicine_in.quantity_prescribed
            )
            session.add(prescription_medicine)
    
    session.add(prescription)
    session.commit()
    session.refresh(prescription)
    
    # Reload with eager loading of medicines and case
    statement = (
        select(Prescription)
        .where(Prescription.id == prescription.id)
        .options(
            selectinload(Prescription.medicines).selectinload(PrescriptionMedicine.medicine),
            selectinload(Prescription.case).selectinload(PatientCase.patient)
        )
    )
    prescription = session.exec(statement).one()
    
    # Build response with patient_name, case_number, and medicines
    rx_data = prescription.model_dump(exclude={"medicines"})
    if prescription.case:
        rx_data['patient_name'] = prescription.case.patient.full_name if prescription.case.patient else None
        rx_data['case_number'] = prescription.case.case_number
    
    # Convert medicines to response format
    medicines_list = []
    for pm in prescription.medicines:
        medicine_dict = {
            "id": pm.id,
            "medicine_id": pm.medicine_id,
            "quantity_prescribed": pm.quantity_prescribed,
            "frequency": pm.frequency,
            "medicine": {
                "id": pm.medicine.id,
                "name": pm.medicine.name,
                "potency": pm.medicine.potency,
                "form": pm.medicine.form
            }
        }
        medicines_list.append(medicine_dict)
    
    rx_data['medicines'] = medicines_list
    return PrescriptionPublic(**rx_data)


@router.delete("/{prescription_id}", response_model=Message)
def delete_prescription(
    session: SessionDep,
    current_user: CurrentUser,
    prescription_id: uuid.UUID
) -> Message:
    """
    Delete a prescription.
    Automatically deletes related follow-ups and associated audit records if any exist.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete prescriptions")
    
    prescription = session.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this prescription")
    
    # Get all related follow-ups first
    related_followups = session.exec(
        select(FollowUp)
        .where(FollowUp.prescription_id == prescription_id)
    ).all()
    
    followup_ids = [fu.id for fu in related_followups]
    
    # Delete audit records that reference these follow-ups (must happen before deleting follow-ups)
    if followup_ids:
        audit_records = session.exec(
            select(OnsiteConsultationAudit)
            .where(OnsiteConsultationAudit.follow_up_id.in_(followup_ids))
        ).all()
        
        for audit in audit_records:
            session.delete(audit)
    
    # Delete related follow-ups
    for followup in related_followups:
        session.delete(followup)
    
    # Delete medicine relationships
    related_medicines = session.exec(
        select(PrescriptionMedicine)
        .where(PrescriptionMedicine.prescription_id == prescription_id)
    ).all()
    
    for pm in related_medicines:
        session.delete(pm)
    
    # Finally delete the prescription itself
    session.delete(prescription)
    session.commit()
    return Message(message="Prescription deleted successfully")


@router.get("/{prescription_id}/print")
def print_prescription(
    session: SessionDep,
    current_user: CurrentUser,
    prescription_id: uuid.UUID
) -> Any:
    """
    Get prescription details for printing.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can print prescriptions")
    
    prescription = session.get(Prescription, prescription_id)
    if not prescription or prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get prescription with medicines and patient details
    statement = (
        select(Prescription)
        .where(Prescription.id == prescription_id)
        .options(
            selectinload(Prescription.medicines),
            selectinload(Prescription.case).selectinload(PatientCase.patient)
        )
    )
    
    prescription = session.exec(statement).one()
    
    # Format for printing
    return {
        "prescription": prescription,
        "patient": prescription.case.patient,
        "medicines": [
            {
                "name": pm.medicine.name,
                "potency": pm.medicine.potency,
                "form": pm.medicine.form,
                "quantity_prescribed": pm.quantity_prescribed,
                "dosage": prescription.dosage,
                "prescription_duration": prescription.prescription_duration,
                "instructions": prescription.instructions
            }
            for pm in prescription.medicines
        ],
        "doctor": current_user,
        "print_date": date.today().isoformat()
    }