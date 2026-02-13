# models/medicine_models.py
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
import sqlalchemy as sa


class ScaleEnum(str, Enum):
    C = "C"
    X = "X"
    Q = "Q"



class FormEnum(str, Enum):
    DISKETTE = "Diskette"
    SOM = "SOM"
    BLANKETS = "Blankets"
    BIO_CHEMIC = "Bio Chemic"
    PLACEBO = "Placebo"
    GLOBULES = "Globules"
    DROPS = "Drops"


class PackingEnum(str, Enum):
    PACK_10 = "10"
    PACK_30 = "30"
    PACK_100 = "100"
    PACK_200 = "200"
    PACK_450 = "450"
    PACK_500 = "500"
    PACK_1000 = "1000"


# ========== DATABASE MODELS (CRUD) ==========
class Medicine(SQLModel, table=True):
    """DATABASE MODEL for medicine"""
    __tablename__ = "medicine"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, max_length=255)
    description: Optional[str] = Field(default=None)
    
    # Relationships
    doctor_stocks: List["DoctorMedicineStock"] = Relationship(back_populates="medicine")
    prescriptions: List["PrescriptionMedicine"] = Relationship(back_populates="medicine")


class DoctorMedicineStockBase(SQLModel):
    """Base doctor medicine stock model"""
    potency: str = Field(max_length=50)
    potency_scale: ScaleEnum = Field(default=ScaleEnum.C)
    form: FormEnum = Field(default=FormEnum.GLOBULES)
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
    medicine_id: int = Field(
        foreign_key="medicine.id",
        nullable=False,
        index=True
    )
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    
    # Relationships
    medicine: Medicine = Relationship(back_populates="doctor_stocks")
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
    medicine_id: int


class DoctorMedicineStockBulk(SQLModel):
    """API INPUT MODEL for bulk creating stock items"""
    items: List[DoctorMedicineStockCreate]


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
class MedicinePublic(SQLModel):
    """API OUTPUT MODEL for medicine"""
    id: int
    name: str
    description: Optional[str] = None


class MedicinesPublic(SQLModel):
    """API OUTPUT MODEL for list of medicines"""
    data: List[MedicinePublic]
    count: int


class DoctorMedicineStockPublic(DoctorMedicineStockBase):
    """API OUTPUT MODEL for stock items"""
    id: uuid.UUID
    medicine_id: int
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