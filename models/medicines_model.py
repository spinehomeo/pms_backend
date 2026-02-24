# models/medicines_model.py - GLOBAL CATALOG VERSION
import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


# ========== DATABASE MODELS (CRUD) ==========
class MedicineBase(SQLModel):
    """Base medicine model"""
    name: str = Field(index=True, nullable=False, max_length=255)
    description: Optional[str] = Field(default=None)
    potency: str = Field(max_length=50)
    potency_scale: str = Field(default="C", max_length=10)  # Dynamic: C, X, Q - validated via EnumService
    form: str = Field(default="Globules", max_length=100)  # Dynamic: Globules, Dilutions, etc - validated via EnumService
    manufacturer: Optional[str] = Field(default=None, max_length=100)  # Dynamic: validated via EnumService


class Medicine(MedicineBase, table=True):
    """DATABASE MODEL for medicine - GLOBAL CATALOG"""
    __tablename__ = "medicine"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Tracking fields
    created_by_doctor_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = Field(default=False)  # Admin can verify user-added medicines
    
    # Relationships
    created_by: Optional["User"] = Relationship()
    prescriptions: List["PrescriptionMedicine"] = Relationship(back_populates="medicine")
    doctor_preferences: List["DoctorMedicinePreference"] = Relationship(back_populates="medicine")


class DoctorMedicinePreference(SQLModel, table=True):
    """Track which medicines each doctor commonly uses (favorites)"""
    __tablename__ = "doctor_medicine_preference"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    medicine_id: uuid.UUID = Field(
        foreign_key="medicine.id",
        nullable=False,
        index=True
    )
    usage_count: int = Field(default=0)  # Track how often they prescribe it
    last_used: Optional[datetime] = Field(default=None)
    is_favorite: bool = Field(default=False)  # Doctor can manually mark favorites
    
    # Relationships
    doctor: "User" = Relationship()
    medicine: Medicine = Relationship(back_populates="doctor_preferences")


# ========== REQUEST MODELS (API Input) ==========
class MedicineCreate(MedicineBase):
    """API INPUT MODEL for creating medicines"""
    pass


class MedicineUpdate(SQLModel):
    """API INPUT MODEL for updating medicines"""
    name: Optional[str] = None
    description: Optional[str] = None
    potency: Optional[str] = None
    potency_scale: Optional[str] = None
    form: Optional[str] = None
    manufacturer: Optional[str] = None
    is_verified: Optional[bool] = None  # Only admins can update this


class QuickAddMedicineRequest(SQLModel):
    """Quick add medicine during prescription creation"""
    name: str
    potency: str
    potency_scale: str = "C"
    form: str = "Globules"
    manufacturer: Optional[str] = None
    description: Optional[str] = None


# ========== RESPONSE MODELS (API Output) ==========
class MedicinePublic(MedicineBase):
    """API OUTPUT MODEL for medicine"""
    id: uuid.UUID
    created_by_doctor_id: Optional[uuid.UUID] = None
    created_at: datetime
    is_verified: bool
    is_favorite: Optional[bool] = None  # Set if fetched for specific doctor


class MedicinesPublic(SQLModel):
    """API OUTPUT MODEL for list of medicines"""
    data: List[MedicinePublic]
    count: int