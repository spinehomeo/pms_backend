# api/routes/prescriptions.py - WITH QUICK-ADD MEDICINE CAPABILITY
import uuid
from typing import Any, List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, SessionDep
from models.prescriptions_model import (
    Prescription, PrescriptionCreate, PrescriptionPublic, PrescriptionsPublic,
    PrescriptionMedicine, PrescriptionMedicineCreate, RepetitionEnum, PrescriptionType,
    PrescriptionUpdate
)
from models.medicines_model import Medicine
from models.patients_model import Patient
from models.cases_model import PatientCase
from models.login_model import Message

router = APIRouter(prefix="/prescriptions", tags=["📋 Prescriptions"])


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


@router.post("/", response_model=PrescriptionPublic)
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
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create prescriptions")
    
    # Verify case belongs to doctor
    case = session.get(PatientCase, prescription_in.case_id)
    if not case or case.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Generate prescription number
    today = date.today()
    year_month = today.strftime("%Y-%m")
    
    prescription_count = session.exec(
        select(func.count())
        .select_from(Prescription)
        .where(
            Prescription.doctor_id == current_user.id,
            func.extract('year', Prescription.prescription_date) == today.year,
            func.extract('month', Prescription.prescription_date) == today.month
        )
    ).one()
    
    prescription_number = f"RX-{year_month}-{prescription_count + 1:03d}"
    
    # Create prescription
    prescription_data = prescription_in.model_dump(exclude={"medicines"})
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
            quantity_prescribed=medicine_in.quantity_prescribed
        )
        session.add(prescription_medicine)

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


@router.delete("/{prescription_id}")
def delete_prescription(
    session: SessionDep,
    current_user: CurrentUser,
    prescription_id: uuid.UUID
) -> Message:
    """
    Delete a prescription.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete prescriptions")
    
    prescription = session.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this prescription")
    
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