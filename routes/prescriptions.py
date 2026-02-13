# api/routes/prescriptions.py
import uuid
from typing import Any, List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select
from sqlalchemy.orm import selectinload

from api.deps import CurrentUser, SessionDep
from models.prescriptions_model import (
    Prescription, PrescriptionCreate, PrescriptionPublic, PrescriptionsPublic,
    PrescriptionMedicine, PrescriptionMedicineCreate
)
from models.medicines_model import DoctorMedicineStock, Medicine
from models.patients_model import Patient
from models.cases_model import PatientCase
from models.login_model import Message

router = APIRouter(prefix="/prescriptions", tags=["📝 Prescriptions"])


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
        .offset(skip)
        .limit(limit)
        .order_by(Prescription.prescription_date.desc())
    )
    
    if case_id:
        # Verify case belongs to doctor
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
    
    return PrescriptionsPublic(data=prescriptions, count=count)


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
    
    prescription = session.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this prescription")
    
    return prescription


@router.post("/", response_model=PrescriptionPublic)
def create_prescription(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    prescription_in: PrescriptionCreate
) -> Any:
    """
    Create new prescription with medicines.
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

    # Perform creation and stock updates atomically
    with session.begin():
        session.add(prescription)
        session.flush()  # Get prescription ID for medicine relationships

        # Add medicines to prescription
        for medicine_in in prescription_in.medicines:
            # Verify medicine exists first so we can use its name in errors
            medicine = session.get(Medicine, medicine_in.medicine_id)
            if not medicine:
                raise HTTPException(
                    status_code=404,
                    detail=f"Medicine {medicine_in.medicine_id} not found"
                )

            # Verify stock belongs to doctor and has sufficient quantity
            stock = session.get(DoctorMedicineStock, medicine_in.stock_id)
            if not stock or stock.doctor_id != current_user.id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Stock item {medicine_in.stock_id} not found or not accessible"
                )

            if stock.quantity < medicine_in.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {medicine.name}. "
                           f"Available: {stock.quantity}, Requested: {medicine_in.quantity}"
                )

            # Create prescription medicine relationship
            prescription_medicine = PrescriptionMedicine(
                prescription_id=prescription.id,
                medicine_id=medicine_in.medicine_id,
                stock_used_id=medicine_in.stock_id,
                quantity_used=medicine_in.quantity
            )
            session.add(prescription_medicine)

            # Update stock quantity
            stock.quantity -= medicine_in.quantity
            stock.last_used_date = today
            session.add(stock)

    session.refresh(prescription)
    return prescription


@router.put("/{prescription_id}", response_model=PrescriptionPublic)
def update_prescription(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    prescription_id: uuid.UUID,
    prescription_in: PrescriptionCreate
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
    
    # Verify case belongs to doctor
    case = session.get(PatientCase, prescription_in.case_id)
    if not case or case.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # For simplicity, delete old medicines, restore stock, and add new ones
    # Do the whole update operation atomically to avoid partial failures
    with session.begin():
        # Remove old prescription medicines and restore stock
        old_prescription_medicines = session.exec(
            select(PrescriptionMedicine)
            .where(PrescriptionMedicine.prescription_id == prescription_id)
        ).all()

        for old_pm in old_prescription_medicines:
            stock = session.get(DoctorMedicineStock, old_pm.stock_used_id)
            if stock:
                stock.quantity += old_pm.quantity_used
                session.add(stock)
            session.delete(old_pm)

        # Update prescription details
        update_dict = prescription_in.model_dump(exclude={"medicines"})
        prescription.sqlmodel_update(update_dict)
        session.add(prescription)
        session.flush()

        # Add new medicines (same logic as create)
        for medicine_in in prescription_in.medicines:
            # Verify medicine exists first
            medicine = session.get(Medicine, medicine_in.medicine_id)
            if not medicine:
                raise HTTPException(
                    status_code=404,
                    detail=f"Medicine {medicine_in.medicine_id} not found"
                )

            stock = session.get(DoctorMedicineStock, medicine_in.stock_id)
            if not stock or stock.doctor_id != current_user.id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Stock item {medicine_in.stock_id} not found or not accessible"
                )

            if stock.quantity < medicine_in.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {medicine.name}. "
                           f"Available: {stock.quantity}, Requested: {medicine_in.quantity}"
                )

            prescription_medicine = PrescriptionMedicine(
                prescription_id=prescription.id,
                medicine_id=medicine_in.medicine_id,
                stock_used_id=medicine_in.stock_id,
                quantity_used=medicine_in.quantity
            )
            session.add(prescription_medicine)

            stock.quantity -= medicine_in.quantity
            stock.last_used_date = date.today()
            session.add(stock)

    session.refresh(prescription)
    return prescription


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
    
    # Restore stock quantities before deleting
    prescription_medicines = session.exec(
        select(PrescriptionMedicine)
        .where(PrescriptionMedicine.prescription_id == prescription_id)
    ).all()
    
    for pm in prescription_medicines:
        stock = session.get(DoctorMedicineStock, pm.stock_used_id)
        if stock:
            stock.quantity += pm.quantity_used
            session.add(stock)
    
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
                "potency": pm.stock_used.potency,
                "form": pm.stock_used.form,
                "dosage": prescription.dosage,
                "duration": prescription.duration,
                "instructions": prescription.instructions
            }
            for pm in prescription.medicines
        ],
        "doctor": current_user,
        "print_date": date.today().isoformat()
    }