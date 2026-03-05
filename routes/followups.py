# api/routes/followups.py
import uuid
from typing import Any, List, Optional, Dict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select

from api.deps import CurrentUser, SessionDep
from models.followups_model import (
    FollowUp, FollowUpCreate, FollowUpUpdate, FollowUpPublic, FollowUpsPublic,
)
from models.doctor_preferences_model import DoctorFollowUpFieldPreference, FOLLOWUP_STANDARD_FIELDS
from models.patients_model import Patient
from models.prescriptions_model import Prescription
from models.cases_model import PatientCase
from models.login_model import Message
from utils.enum_service import EnumService

router = APIRouter(prefix="/followups", tags=["🔔 Follow-ups"])


def validate_followup_fields(
    doctor_id: uuid.UUID, 
    followup_data: Dict[str, Any], 
    session: SessionDep
) -> Dict[str, Any]:
    """
    Validate follow-up fields against doctor's preferences and check required fields.
    """
    # Get doctor's field preferences
    preferences = session.exec(
        select(DoctorFollowUpFieldPreference).where(
            DoctorFollowUpFieldPreference.doctor_id == doctor_id
        )
    ).all()
    
    # Create a dictionary of preferences by field name
    pref_dict = {pref.field_name: pref for pref in preferences}
    
    # Check required fields
    for pref in preferences:
        if pref.is_required and pref.is_enabled:
            field_value = followup_data.get(pref.field_name)
            if field_value is None or (isinstance(field_value, str) and field_value.strip() == ""):
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field '{pref.display_name}' is missing or empty"
                )
    
    # Filter custom_fields to only include enabled custom fields
    custom_fields = followup_data.get("custom_fields")
    if custom_fields:
        # Get enabled custom fields (non-standard fields)
        standard_field_names = {f["field_name"] for f in FOLLOWUP_STANDARD_FIELDS}
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
        followup_data["custom_fields"] = validated_custom or None
    
    return followup_data


@router.get("/", response_model=FollowUpsPublic)
def read_followups(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    case_id: Optional[uuid.UUID] = None,
    patient_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    upcoming: bool = False
) -> Any:
    """
    Retrieve follow-ups with filtering options.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access follow-ups")
    
    # Base query
    count_statement = (
        select(func.count())
        .select_from(FollowUp)
        .where(FollowUp.doctor_id == current_user.id)
    )
    
    statement = (
        select(FollowUp)
        .where(FollowUp.doctor_id == current_user.id)
        .order_by(FollowUp.follow_up_date.desc())
        .offset(skip)
        .limit(limit)
    )
    
    # Apply filters
    if case_id:
        # Verify case belongs to doctor
        case = session.get(PatientCase, case_id)
        if not case or case.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Case not found")
        
        count_statement = count_statement.where(FollowUp.case_id == case_id)
        statement = statement.where(FollowUp.case_id == case_id)
    
    if patient_id:
        # Verify patient belongs to doctor
        patient = session.get(Patient, patient_id)
        if not patient or patient.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Get cases for this patient
        patient_cases = session.exec(
            select(PatientCase.id).where(PatientCase.patient_id == patient_id)
        ).all()
        
        if patient_cases:
            count_statement = count_statement.where(FollowUp.case_id.in_(patient_cases))
            statement = statement.where(FollowUp.case_id.in_(patient_cases))
    
    if from_date:
        count_statement = count_statement.where(FollowUp.follow_up_date >= from_date)
        statement = statement.where(FollowUp.follow_up_date >= from_date)
    
    if to_date:
        count_statement = count_statement.where(FollowUp.follow_up_date <= to_date)
        statement = statement.where(FollowUp.follow_up_date <= to_date)
    
    if upcoming:
        today = date.today()
        future_date = today.replace(day=today.day + 30)  # Next 30 days
        
        count_statement = count_statement.where(
            FollowUp.next_follow_up_date >= today
        ).where(
            FollowUp.next_follow_up_date <= future_date
        )
        statement = statement.where(
            FollowUp.next_follow_up_date >= today
        ).where(
            FollowUp.next_follow_up_date <= future_date
        ).order_by(FollowUp.next_follow_up_date.asc())
    
    count = session.exec(count_statement).one()
    followups = session.exec(statement).all()
    
    # Populate patient and case details
    response_followups = []
    for followup in followups:
        followup_dict = {
            **followup.__dict__,
            "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
            "case_number": followup.case.case_number if followup.case else None
        }
        response_followups.append(FollowUpPublic(**followup_dict))
    
    return FollowUpsPublic(data=response_followups, count=count)


@router.get("/{followup_id}", response_model=FollowUpPublic)
def read_followup(
    session: SessionDep,
    current_user: CurrentUser,
    followup_id: uuid.UUID
) -> Any:
    """
    Get follow-up by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access follow-ups")
    
    followup = session.get(FollowUp, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    if followup.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this follow-up")
    
    followup_dict = {
        **followup.__dict__,
        "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
        "case_number": followup.case.case_number if followup.case else None
    }
    return FollowUpPublic(**followup_dict)


@router.post("/", response_model=FollowUpPublic)
def create_followup(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    followup_in: FollowUpCreate
) -> Any:
    """
    Create new follow-up.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create follow-ups")
    
    # Verify case belongs to doctor
    case = session.get(PatientCase, followup_in.case_id)
    if not case or case.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify prescription belongs to doctor and case
    prescription = session.get(Prescription, followup_in.prescription_id)
    if not prescription or prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.case_id != followup_in.case_id:
        raise HTTPException(
            status_code=400,
            detail="Prescription does not belong to the specified case"
        )
    
    # Calculate interval from last follow-up or prescription date
    last_followup = session.exec(
        select(FollowUp)
        .where(FollowUp.case_id == followup_in.case_id)
        .order_by(FollowUp.follow_up_date.desc())
    ).first()
    
    if last_followup:
        interval_days = (date.today() - last_followup.follow_up_date).days
    else:
        interval_days = (date.today() - prescription.prescription_date).days
    
    # Calculate next follow-up date (default: 30 days from now)
    next_follow_up = followup_in.next_follow_up_date or (
        date.today() + timedelta(days=30)
    )
    
    followup_data = followup_in.model_dump()
    followup_data.update({
        "doctor_id": current_user.id,
        "interval_days": max(interval_days, 7),  # Minimum 7 days
        "next_follow_up_date": next_follow_up
    })
    
    # Validate fields and custom fields
    followup_data = validate_followup_fields(current_user.id, followup_data, session)
    
    # Validate status if provided
    if followup_data.get("status"):
        if not EnumService.validate_value(session, "FollowupStatus", followup_data["status"], current_user.id):
            raise HTTPException(status_code=400, detail=f"Invalid follow-up status: {followup_data['status']}")
    
    followup = FollowUp.model_validate(followup_data)
    session.add(followup)
    session.commit()
    session.refresh(followup)
    
    # Update patient's last visit date
    patient = session.get(Patient, case.patient_id)
    if patient:
        patient.last_visit_date = followup.follow_up_date
        session.add(patient)
        session.commit()
    
    followup_dict = {
        **followup.__dict__,
        "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
        "case_number": followup.case.case_number if followup.case else None
    }
    return FollowUpPublic(**followup_dict)


@router.put("/{followup_id}", response_model=FollowUpPublic)
def update_followup(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    followup_id: uuid.UUID,
    followup_in: FollowUpUpdate
) -> Any:
    """
    Update a follow-up.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update follow-ups")
    
    followup = session.get(FollowUp, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    if followup.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this follow-up")
    
    # Verify case and prescription if being updated
    if followup_in.case_id and followup_in.case_id != followup.case_id:
        case = session.get(PatientCase, followup_in.case_id)
        if not case or case.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Case not found")
    
    if followup_in.prescription_id and followup_in.prescription_id != followup.prescription_id:
        prescription = session.get(Prescription, followup_in.prescription_id)
        if not prescription or prescription.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Prescription not found")
    
    update_dict = followup_in.model_dump(exclude_unset=True)
    
    # Validate fields and custom fields
    update_dict = validate_followup_fields(current_user.id, update_dict, session)
    
    # Validate status if provided
    if update_dict.get("status"):
        if not EnumService.validate_value(session, "FollowupStatus", update_dict["status"], current_user.id):
            raise HTTPException(status_code=400, detail=f"Invalid follow-up status: {update_dict['status']}")
    
    followup.sqlmodel_update(update_dict)
    session.add(followup)
    session.commit()
    session.refresh(followup)
    
    followup_dict = {
        **followup.__dict__,
        "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
        "case_number": followup.case.case_number if followup.case else None
    }
    return FollowUpPublic(**followup_dict)


@router.delete("/{followup_id}")
def delete_followup(
    session: SessionDep,
    current_user: CurrentUser,
    followup_id: uuid.UUID
) -> Message:
    """
    Delete a follow-up.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete follow-ups")
    
    followup = session.get(FollowUp, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    if followup.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this follow-up")
    
    session.delete(followup)
    session.commit()
    return Message(message="Follow-up deleted successfully")


@router.get("/case/{case_id}")
def get_case_followups(
    session: SessionDep,
    current_user: CurrentUser,
    case_id: uuid.UUID
) -> Any:
    """
    Get all follow-ups for a case.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access follow-ups")
    
    # Verify case belongs to doctor
    case = session.get(PatientCase, case_id)
    if not case or case.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    followups = session.exec(
        select(FollowUp)
        .where(FollowUp.case_id == case_id)
        .order_by(FollowUp.follow_up_date.asc())
    ).all()
    
    # Populate patient details for followups
    response_followups = []
    for followup in followups:
        followup_dict = {
            **followup.__dict__,
            "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
            "case_number": followup.case.case_number if followup.case else None
        }
        response_followups.append(FollowUpPublic(**followup_dict))
    
    # Calculate follow-up timeline
    timeline = []
    for i, followup in enumerate(response_followups):
        timeline_item = {
            "followup": followup,
            "position": i + 1,
            "total": len(response_followups)
        }
        
        # Calculate days between follow-ups
        if i > 0:
            prev_followup = response_followups[i - 1]
            days_between = (followup.follow_up_date - prev_followup.follow_up_date).days
            timeline_item["days_since_previous"] = days_between
        
        timeline.append(timeline_item)
    
    return {
        "case": case,
        "followups": response_followups,
        "timeline": timeline,
        "total_followups": len(response_followups),
        "first_followup": response_followups[0] if response_followups else None,
        "latest_followup": response_followups[-1] if response_followups else None
    }


@router.get("/upcoming/due")
def get_due_followups(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get follow-ups that are due or overdue.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access follow-ups")
    
    today = date.today()
    
    # Find cases with next_follow_up_date <= today
    due_followups = session.exec(
        select(FollowUp)
        .where(
            FollowUp.doctor_id == current_user.id,
            FollowUp.next_follow_up_date <= today
        )
        .order_by(FollowUp.next_follow_up_date.asc())
    ).all()
    
    # Group by overdue status
    overdue = []
    due_today = []
    upcoming = []
    
    for followup in due_followups:
        followup_dict = {
            **followup.__dict__,
            "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
            "case_number": followup.case.case_number if followup.case else None
        }
        followup_public = FollowUpPublic(**followup_dict)
        
        days_overdue = (today - followup.next_follow_up_date).days
        
        if days_overdue > 0:
            overdue.append({
                "followup": followup_public,
                "days_overdue": days_overdue
            })
        elif days_overdue == 0:
            due_today.append(followup_public)
    
    # Find upcoming follow-ups (next 7 days)
    next_week = today + timedelta(days=7)
    upcoming_followups = session.exec(
        select(FollowUp)
        .where(
            FollowUp.doctor_id == current_user.id,
            FollowUp.next_follow_up_date > today,
            FollowUp.next_follow_up_date <= next_week
        )
        .order_by(FollowUp.next_follow_up_date.asc())
    ).all()
    
    for followup in upcoming_followups:
        followup_dict = {
            **followup.__dict__,
            "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
            "case_number": followup.case.case_number if followup.case else None
        }
        followup_public = FollowUpPublic(**followup_dict)
        
        days_until = (followup.next_follow_up_date - today).days
        upcoming.append({
            "followup": followup_public,
            "days_until": days_until
        })
    
    return {
        "overdue": {
            "count": len(overdue),
            "items": overdue
        },
        "due_today": {
            "count": len(due_today),
            "items": due_today
        },
        "upcoming_week": {
            "count": len(upcoming),
            "items": upcoming
        },
        "total_due": len(due_followups),
        "check_date": today.isoformat()
    }


@router.post("/{followup_id}/schedule-next")
def schedule_next_followup(
    session: SessionDep,
    current_user: CurrentUser,
    followup_id: uuid.UUID,
    next_date: date
) -> Any:
    """
    Schedule next follow-up based on current follow-up.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can schedule follow-ups")
    
    followup = session.get(FollowUp, followup_id)
    if not followup or followup.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    # Create new follow-up record
    new_followup_data = {
        "case_id": followup.case_id,
        "prescription_id": followup.prescription_id,
        "doctor_id": current_user.id,
        "follow_up_date": next_date,
        "interval_days": (next_date - followup.follow_up_date).days
    }
    
    new_followup = FollowUp.model_validate(new_followup_data)
    session.add(new_followup)
    
    # Update current followup's next_follow_up_date
    followup.next_follow_up_date = next_date
    session.add(followup)
    
    session.commit()
    session.refresh(new_followup)
    session.refresh(followup)
    
    # Populate patient details
    followup_dict = {
        **followup.__dict__,
        "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
        "case_number": followup.case.case_number if followup.case else None
    }
    followup_public = FollowUpPublic(**followup_dict)
    
    new_followup_dict = {
        **new_followup.__dict__,
        "patient_name": new_followup.case.patient.full_name if new_followup.case and new_followup.case.patient else None,
        "case_number": new_followup.case.case_number if new_followup.case else None
    }
    new_followup_public = FollowUpPublic(**new_followup_dict)
    
    return {
        "message": "Next follow-up scheduled successfully",
        "current_followup": followup_public,
        "scheduled_followup": new_followup_public
    }


@router.post("/{followup_id}/confirm-payment")
def confirm_followup_payment(
    session: SessionDep,
    current_user: CurrentUser,
    followup_id: uuid.UUID
) -> FollowUpPublic:
    """
    Confirm payment for a follow-up and update status to 'confirmed'.
    
    This marks the follow-up as confirmed after payment has been received.
    The followup transitions from 'scheduled' to 'confirmed' status.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can confirm follow-up payments")
    
    followup = session.get(FollowUp, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    if followup.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to confirm this follow-up payment")
    
    # Update payment confirmation
    followup.payment_confirmed = True
    followup.payment_confirmed_date = datetime.now()
    
    # Update status to 'confirmed'
    if not EnumService.validate_value(session, "FollowupStatus", "confirmed", current_user.id):
        raise HTTPException(status_code=400, detail="Confirmed status is not available for your account")
    
    followup.status = "confirmed"
    
    session.add(followup)
    session.commit()
    session.refresh(followup)
    
    followup_dict = {
        **followup.__dict__,
        "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
        "case_number": followup.case.case_number if followup.case else None
    }
    return FollowUpPublic(**followup_dict)


@router.post("/{followup_id}/close-case")
def close_followup_case(
    session: SessionDep,
    current_user: CurrentUser,
    followup_id: uuid.UUID
) -> FollowUpPublic:
    """
    Close the case associated with a follow-up and update status to 'case_closed'.
    
    This marks the follow-up as case closed, indicating that the patient's
    treatment and follow-ups are complete. The case status will also be updated to 'closed'.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can close cases")
    
    followup = session.get(FollowUp, followup_id)
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    if followup.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to close this case")
    
    # Update followup status to 'case_closed'
    if not EnumService.validate_value(session, "FollowupStatus", "case_closed", current_user.id):
        raise HTTPException(status_code=400, detail="Case closed status is not available for your account")
    
    followup.status = "case_closed"
    
    # Also update the associated case status to 'closed'
    case = session.get(PatientCase, followup.case_id)
    if case:
        # Validate case status enum
        if not EnumService.validate_value(session, "CaseStatus", "closed", current_user.id):
            raise HTTPException(status_code=400, detail="Case closed status is not available for your account")
        
        case.status = "closed"
        session.add(case)
    
    session.add(followup)
    session.commit()
    session.refresh(followup)
    
    followup_dict = {
        **followup.__dict__,
        "patient_name": followup.case.patient.full_name if followup.case and followup.case.patient else None,
        "case_number": followup.case.case_number if followup.case else None
    }
    return FollowUpPublic(**followup_dict)
