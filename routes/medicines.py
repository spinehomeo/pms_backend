# api/routes/medicines.py
import uuid
from typing import Any, List, Optional
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select, and_

from api.deps import CurrentUser, SessionDep
from models.medicines_model import (
    MedicineMaster, DoctorMedicineStock, DoctorMedicineStockCreate, 
    DoctorMedicineStockUpdate, DoctorMedicineStockPublic, MedicinesStockPublic,
    MedicineMasterPublic, MedicinesPublic, MedicineForm, PotencyScale,
    MedicineUsageLog
)
from models.prescriptions_model import PrescriptionMedicine
from models.login_model import Message

router = APIRouter(prefix="/medicines", tags=["💊 Medicines"])


@router.get("/master", response_model=MedicinesPublic)
def read_medicines_master(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    kingdom: Optional[str] = None
) -> Any:
    """
    Retrieve medicine master list.
    """
    # Both doctors and superusers can access medicine master
    if not current_user.is_doctor and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    count_statement = select(func.count()).select_from(MedicineMaster)
    statement = select(MedicineMaster).offset(skip).limit(limit)
    
    if search:
        search_filter = f"%{search}%"
        count_statement = count_statement.where(
            MedicineMaster.name.ilike(search_filter) |
            MedicineMaster.abbreviation.ilike(search_filter) |
            MedicineMaster.common_indicators.ilike(search_filter)
        )
        statement = statement.where(
            MedicineMaster.name.ilike(search_filter) |
            MedicineMaster.abbreviation.ilike(search_filter) |
            MedicineMaster.common_indicators.ilike(search_filter)
        )
    
    if kingdom:
        count_statement = count_statement.where(MedicineMaster.kingdom == kingdom)
        statement = statement.where(MedicineMaster.kingdom == kingdom)
    
    count = session.exec(count_statement).one()
    medicines = session.exec(statement).all()
    
    return MedicinesPublic(data=medicines, count=count)


@router.get("/master/{medicine_id}", response_model=MedicineMasterPublic)
def read_medicine_master(
    session: SessionDep,
    current_user: CurrentUser,
    medicine_id: uuid.UUID
) -> Any:
    """
    Get medicine from master list by ID.
    """
    if not current_user.is_doctor and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    medicine = session.get(MedicineMaster, medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    return medicine


@router.get("/stock", response_model=MedicinesStockPublic)
def read_medicine_stock(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    low_stock: bool = False,
    expired: bool = False,
    medicine_id: Optional[uuid.UUID] = None
) -> Any:
    """
    Retrieve doctor's medicine stock.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access stock")
    
    # Base query for doctor's stock
    count_statement = (
        select(func.count())
        .select_from(DoctorMedicineStock)
        .where(DoctorMedicineStock.doctor_id == current_user.id)
    )
    
    statement = (
        select(DoctorMedicineStock)
        .where(DoctorMedicineStock.doctor_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        # Join with MedicineMaster for search
        count_statement = (
            count_statement
            .join(MedicineMaster)
            .where(MedicineMaster.name.ilike(search_filter))
        )
        statement = (
            statement
            .join(MedicineMaster)
            .where(MedicineMaster.name.ilike(search_filter))
        )
    
    if low_stock:
        count_statement = count_statement.where(
            DoctorMedicineStock.quantity <= DoctorMedicineStock.low_stock_threshold
        )
        statement = statement.where(
            DoctorMedicineStock.quantity <= DoctorMedicineStock.low_stock_threshold
        )
    
    if expired:
        today = date.today()
        count_statement = count_statement.where(
            DoctorMedicineStock.expiry_date < today
        )
        statement = statement.where(
            DoctorMedicineStock.expiry_date < today
        )
    
    if medicine_id:
        count_statement = count_statement.where(
            DoctorMedicineStock.medicine_id == medicine_id
        )
        statement = statement.where(
            DoctorMedicineStock.medicine_id == medicine_id
        )
    
    count = session.exec(count_statement).one()
    stock_items = session.exec(statement).all()
    
    return MedicinesStockPublic(data=stock_items, count=count)


@router.get("/stock/{stock_id}", response_model=DoctorMedicineStockPublic)
def read_stock_item(
    session: SessionDep,
    current_user: CurrentUser,
    stock_id: uuid.UUID
) -> Any:
    """
    Get stock item by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access stock")
    
    stock_item = session.get(DoctorMedicineStock, stock_id)
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    if stock_item.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this stock item")
    
    return stock_item


@router.post("/stock", response_model=DoctorMedicineStockPublic)
def create_stock_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    stock_in: DoctorMedicineStockCreate
) -> Any:
    """
    Add new medicine to stock.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add to stock")
    
    # Verify medicine exists in master
    medicine = session.get(MedicineMaster, stock_in.medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found in master list")
    
    # Check if same medicine with same potency and form already exists
    existing = session.exec(
        select(DoctorMedicineStock).where(
            DoctorMedicineStock.doctor_id == current_user.id,
            DoctorMedicineStock.medicine_id == stock_in.medicine_id,
            DoctorMedicineStock.potency == stock_in.potency,
            DoctorMedicineStock.form == stock_in.form
        )
    ).first()
    
    if existing:
        # Update existing stock instead of creating new
        existing.quantity += stock_in.quantity
        existing.purchase_date = stock_in.purchase_date or date.today()
        existing.batch_number = stock_in.batch_number or existing.batch_number
        existing.expiry_date = stock_in.expiry_date or existing.expiry_date
        existing.manufacturer = stock_in.manufacturer or existing.manufacturer
        
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    
    # Create new stock item
    stock_item = DoctorMedicineStock.model_validate(
        stock_in,
        update={"doctor_id": current_user.id}
    )
    session.add(stock_item)
    session.commit()
    session.refresh(stock_item)
    return stock_item


@router.put("/stock/{stock_id}", response_model=DoctorMedicineStockPublic)
def update_stock_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    stock_id: uuid.UUID,
    stock_in: DoctorMedicineStockUpdate
) -> Any:
    """
    Update stock item.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update stock")
    
    stock_item = session.get(DoctorMedicineStock, stock_id)
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    if stock_item.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this stock item")
    
    update_dict = stock_in.model_dump(exclude_unset=True)
    stock_item.sqlmodel_update(update_dict)
    session.add(stock_item)
    session.commit()
    session.refresh(stock_item)
    return stock_item


@router.delete("/stock/{stock_id}")
def delete_stock_item(
    session: SessionDep,
    current_user: CurrentUser,
    stock_id: uuid.UUID
) -> Message:
    """
    Delete stock item.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete stock")
    
    stock_item = session.get(DoctorMedicineStock, stock_id)
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    if stock_item.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this stock item")
    
    # Check if stock is being used in any prescriptions
    usage_count = session.exec(
        select(func.count())
        .select_from(PrescriptionMedicine)
        .where(PrescriptionMedicine.stock_used_id == stock_id)
    ).one()
    
    if usage_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete stock item that is being used in prescriptions. "
                  "Set is_active to False instead."
        )
    
    session.delete(stock_item)
    session.commit()
    return Message(message="Stock item deleted successfully")


@router.get("/stock/{stock_id}/usage")
def get_stock_usage(
    session: SessionDep,
    current_user: CurrentUser,
    stock_id: uuid.UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Any:
    """
    Get usage history for a stock item.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access usage history")
    
    stock_item = session.get(DoctorMedicineStock, stock_id)
    if not stock_item or stock_item.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    statement = select(MedicineUsageLog).where(
        MedicineUsageLog.stock_item_id == stock_id
    )
    
    if from_date:
        statement = statement.where(MedicineUsageLog.used_date >= from_date)
    
    if to_date:
        statement = statement.where(MedicineUsageLog.used_date <= to_date)
    
    usage_logs = session.exec(statement.order_by(MedicineUsageLog.used_date.desc())).all()
    
    total_used = sum(log.quantity_used for log in usage_logs)
    
    return {
        "stock_item": stock_item,
        "usage_logs": usage_logs,
        "total_used": total_used,
        "remaining": stock_item.quantity
    }


@router.get("/alerts/low-stock")
def get_low_stock_alerts(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get low stock alerts.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access alerts")
    
    statement = (
        select(DoctorMedicineStock)
        .where(
            and_(
                DoctorMedicineStock.doctor_id == current_user.id,
                DoctorMedicineStock.is_active == True,
                DoctorMedicineStock.quantity <= DoctorMedicineStock.low_stock_threshold
            )
        )
    )
    
    low_stock_items = session.exec(statement).all()
    
    return {
        "count": len(low_stock_items),
        "items": low_stock_items,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/alerts/expiring")
def get_expiring_medicines(
    session: SessionDep,
    current_user: CurrentUser,
    days: int = 30
) -> Any:
    """
    Get medicines expiring soon.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access alerts")
    
    today = date.today()
    expiry_threshold = today.replace(day=today.day + days)
    
    statement = (
        select(DoctorMedicineStock)
        .where(
            and_(
                DoctorMedicineStock.doctor_id == current_user.id,
                DoctorMedicineStock.is_active == True,
                DoctorMedicineStock.expiry_date != None,
                DoctorMedicineStock.expiry_date <= expiry_threshold,
                DoctorMedicineStock.expiry_date >= today
            )
        )
        .order_by(DoctorMedicineStock.expiry_date.asc())
    )
    
    expiring_items = session.exec(statement).all()
    
    return {
        "count": len(expiring_items),
        "items": expiring_items,
        "expiry_threshold": expiry_threshold.isoformat(),
        "timestamp": datetime.now().isoformat()
    }