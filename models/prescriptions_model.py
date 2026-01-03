# models/prescription_models.py
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum


class PrescriptionType(str, Enum):
    ACUTE = "acute"
    CHRONIC = "chronic"
    CONSTITUTIONAL = "constitutional"
    INTERCURRENT = "intercurrent"
    NOSODE = "nosode"
    SARCODE = "sarcode"
    TAUTODE = "tautode"


# ========== DATABASE MODELS (CRUD) ==========
class PrescriptionBase(SQLModel):
    """Base prescription model"""
    prescription_type: PrescriptionType = Field(default=PrescriptionType.CHRONIC)
    dosage: str = Field(max_length=200)
    duration: str = Field(max_length=100)
    instructions: Optional[str] = Field(default=None)
    follow_up_advice: Optional[str] = Field(default=None)
    dietary_restrictions: Optional[str] = Field(default=None)
    avoidance: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class Prescription(PrescriptionBase, table=True):
    """DATABASE MODEL for prescriptions - USED FOR CRUD"""
    __tablename__ = "prescription"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="patient_case.id",
        nullable=False,
        index=True
    )
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    prescription_date: date = Field(default_factory=date.today)
    prescription_number: str = Field(max_length=50, unique=True, index=True)
    
    # Relationships
    case: "PatientCase" = Relationship(back_populates="prescription")
    doctor: "User" = Relationship(back_populates="prescriptions")
    medicines: List["PrescriptionMedicine"] = Relationship(back_populates="prescription")
    follow_up: Optional["FollowUp"] = Relationship(back_populates="prescription")


class PrescriptionMedicine(SQLModel, table=True):
    """DATABASE MODEL for prescription-medicine mapping - USED FOR CRUD"""
    __tablename__ = "prescription_medicine"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prescription_id: uuid.UUID = Field(
        foreign_key="prescription.id",
        nullable=False,
        index=True
    )
    medicine_id: uuid.UUID = Field(
        foreign_key="medicine_master.id",
        nullable=False,
        index=True
    )
    stock_used_id: uuid.UUID = Field(
        foreign_key="doctor_medicine_stock.id",
        nullable=False
    )
    quantity_used: float = Field(default=1.0, ge=0)
    
    # Relationships
    prescription: Prescription = Relationship(back_populates="medicines")
    medicine: "MedicineMaster" = Relationship(back_populates="prescriptions")
    stock_used: "DoctorMedicineStock" = Relationship(back_populates="prescriptions")


# ========== REQUEST MODELS (API Input) ==========
class PrescriptionMedicineCreate(SQLModel):
    """API INPUT MODEL for prescription medicines"""
    medicine_id: uuid.UUID
    stock_id: uuid.UUID
    quantity: float = Field(default=1.0, ge=0)


class PrescriptionCreate(PrescriptionBase):
    """API INPUT MODEL for creating prescriptions"""
    case_id: uuid.UUID
    medicines: List[PrescriptionMedicineCreate] = []


class PrescriptionUpdate(SQLModel):
    """API INPUT MODEL for updating prescriptions"""
    dosage: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    follow_up_advice: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    avoidance: Optional[str] = None
    notes: Optional[str] = None


# ========== RESPONSE MODELS (API Output) ==========
class PrescriptionMedicinePublic(SQLModel):
    """API OUTPUT MODEL for prescription medicines"""
    id: uuid.UUID
    medicine_id: uuid.UUID
    stock_used_id: uuid.UUID
    quantity_used: float
    medicine_name: Optional[str] = None
    potency: Optional[str] = None
    form: Optional[str] = None


class PrescriptionPublic(PrescriptionBase):
    """API OUTPUT MODEL for single prescription"""
    id: uuid.UUID
    case_id: uuid.UUID
    doctor_id: uuid.UUID
    prescription_date: date
    prescription_number: str
    medicines: List[PrescriptionMedicinePublic] = []
    patient_name: Optional[str] = None
    case_number: Optional[str] = None


class PrescriptionsPublic(SQLModel):
    """API OUTPUT MODEL for list of prescriptions"""
    data: List[PrescriptionPublic]
    count: int


class PrintPrescriptionResponse(SQLModel):
    """API OUTPUT MODEL for printing prescriptions"""
    prescription: PrescriptionPublic
    patient: dict
    doctor: dict
    print_date: str