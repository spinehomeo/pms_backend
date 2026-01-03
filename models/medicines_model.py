# models/medicine_models.py
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
import sqlalchemy as sa


class MedicineForm(str, Enum):
    PILLS = "pills"
    GLOBULES = "globules"
    DROPS = "drops"
    POWDER = "powder"
    OINTMENT = "ointment"
    SUPPOSITORY = "suppository"
    INJECTION = "injection"


class PotencyScale(str, Enum):
    X = "X"
    C = "C"
    LM = "LM"
    Q = "Q"
    M = "M"
    CM = "CM"
    MM = "MM"


# ========== DATABASE MODELS (CRUD) ==========
class MedicineMasterBase(SQLModel):
    """Base medicine master model"""
    name: str = Field(max_length=255, nullable=False, index=True)
    abbreviation: Optional[str] = Field(default=None, max_length=50)
    kingdom: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None)
    common_indicators: Optional[str] = Field(default=None)
    key_symptoms: Optional[str] = Field(default=None)
    modalities: Optional[str] = Field(default=None)
    temperament: Optional[str] = Field(default=None)
    miasmatic_background: Optional[str] = Field(default=None)
    repertory_rubrics: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class MedicineMaster(MedicineMasterBase, table=True):
    """DATABASE MODEL for medicine master - USED FOR CRUD"""
    __tablename__ = "medicine_master"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Relationships
    doctor_stocks: List["DoctorMedicineStock"] = Relationship(back_populates="medicine")
    prescriptions: List["PrescriptionMedicine"] = Relationship(back_populates="medicine")


class DoctorMedicineStockBase(SQLModel):
    """Base doctor medicine stock model"""
    potency: str = Field(max_length=50)
    potency_scale: PotencyScale = Field(default=PotencyScale.C)
    form: MedicineForm = Field(default=MedicineForm.GLOBULES)
    quantity: float = Field(default=0.0, ge=0)
    unit: str = Field(default="packet", max_length=50)
    batch_number: Optional[str] = Field(default=None, max_length=100)
    expiry_date: Optional[date] = Field(default=None)
    manufacturer: Optional[str] = Field(default=None, max_length=255)
    purchase_date: date = Field(default_factory=date.today)
    last_used_date: Optional[date] = Field(default=None)
    storage_location: str = Field(default="Clinic Cabinet A", max_length=255)
    is_active: bool = Field(default=True)
    low_stock_threshold: float = Field(default=5.0, ge=0)


class DoctorMedicineStock(DoctorMedicineStockBase, table=True):
    """DATABASE MODEL for doctor's medicine stock - USED FOR CRUD"""
    __tablename__ = "doctor_medicine_stock"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    medicine_id: uuid.UUID = Field(
        foreign_key="medicine_master.id",
        nullable=False,
        index=True
    )
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    
    # Relationships
    medicine: MedicineMaster = Relationship(back_populates="doctor_stocks")
    doctor: "User" = Relationship(back_populates="medicine_stock")
    prescriptions: List["PrescriptionMedicine"] = Relationship(back_populates="stock_used")


class MedicineUsageLog(SQLModel, table=True):
    """DATABASE MODEL for medicine usage logs - USED FOR CRUD"""
    __tablename__ = "medicine_usage_log"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    stock_item_id: uuid.UUID = Field(
        foreign_key="doctor_medicine_stock.id",
        nullable=False,
        index=True
    )
    prescription_id: uuid.UUID = Field(
        foreign_key="prescription.id",
        nullable=False,
        index=True
    )
    patient_id: uuid.UUID = Field(
        foreign_key="patient.id",
        nullable=False,
        index=True
    )
    quantity_used: float = Field(ge=0)
    used_date: date = Field(default_factory=date.today)
    
    # Index for reporting
    __table_args__ = (
        sa.Index('idx_usage_by_date', 'used_date'),
    )
    
    # Relationships
    stock_item: DoctorMedicineStock = Relationship()
    prescription: "Prescription" = Relationship()
    patient: "Patient" = Relationship()


# ========== REQUEST MODELS (API Input) ==========
class DoctorMedicineStockCreate(DoctorMedicineStockBase):
    """API INPUT MODEL for creating stock items"""
    medicine_id: uuid.UUID


class DoctorMedicineStockUpdate(SQLModel):
    """API INPUT MODEL for updating stock items"""
    quantity: Optional[float] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    manufacturer: Optional[str] = None
    storage_location: Optional[str] = None
    is_active: Optional[bool] = None
    low_stock_threshold: Optional[float] = None


# ========== RESPONSE MODELS (API Output) ==========
class MedicineMasterPublic(MedicineMasterBase):
    """API OUTPUT MODEL for medicine master"""
    id: uuid.UUID


class MedicinesPublic(SQLModel):
    """API OUTPUT MODEL for list of medicines from master"""
    data: List[MedicineMasterPublic]
    count: int


class DoctorMedicineStockPublic(DoctorMedicineStockBase):
    """API OUTPUT MODEL for stock items"""
    id: uuid.UUID
    medicine_id: uuid.UUID
    doctor_id: uuid.UUID
    medicine_name: Optional[str] = None


class MedicinesStockPublic(SQLModel):
    """API OUTPUT MODEL for list of stock items"""
    data: List[DoctorMedicineStockPublic]
    count: int


class StockUsageResponse(SQLModel):
    """API OUTPUT MODEL for stock usage"""
    stock_item: DoctorMedicineStockPublic
    usage_logs: List[dict] = []
    total_used: float = 0.0
    remaining: float = 0.0


class StockAlertsResponse(SQLModel):
    """API OUTPUT MODEL for stock alerts"""
    low_stock_count: int = 0
    expiring_soon_count: int = 0
    expired_count: int = 0
    low_stock_items: List[DoctorMedicineStockPublic] = []
    expiring_items: List[DoctorMedicineStockPublic] = []
    expired_items: List[DoctorMedicineStockPublic] = []