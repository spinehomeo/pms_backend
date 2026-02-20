# models/enum_option_model.py
"""
Dynamic enum system models - allows admin to create and manage enums at runtime.
Architecture:
  - EnumType: Registry of all available enum types (e.g., "AppointmentStatus")
  - EnumOption: Individual options within an enum type
  - DoctorEnumPreference: Per-doctor toggle to enable/disable options
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa


# ============================================================================
# BASE MODELS (for API schemas)
# ============================================================================

class EnumTypeBase(SQLModel):
    """Base enum type model"""
    key: str = Field(max_length=100)            # e.g., "AppointmentStatus"
    label: str = Field(max_length=100)          # e.g., "Appointment Status"
    description: Optional[str] = Field(default=None, max_length=500)
    is_system: bool = Field(default=False)      # True = seeded, cannot delete
    is_active: bool = Field(default=True)       # Admin can disable globally


class EnumOptionBase(SQLModel):
    """Base enum option model"""
    enum_type: str = Field(max_length=100)      # FK reference (not UUID)
    value: str = Field(max_length=255)          # e.g., "Confirmed"
    label: str = Field(max_length=255)          # e.g., "Confirmed (Appointment confirmed)"
    is_active: bool = Field(default=True)
    is_system: bool = Field(default=False)      # True = seeded, cannot delete
    sort_order: int = Field(default=0)


class DoctorEnumPreferenceBase(SQLModel):
    """Base doctor enum preference model"""
    is_enabled: bool = Field(default=True)


# ============================================================================
# DATABASE MODELS (table=True)
# ============================================================================

class EnumType(EnumTypeBase, table=True):
    """DATABASE MODEL for enum type registry"""
    __tablename__ = "enum_types"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    options: List["EnumOption"] = Relationship(back_populates="enum_type_obj")
    
    __table_args__ = (
        sa.Index('idx_enum_type_key', 'key', unique=True),
        sa.Index('idx_enum_type_active', 'is_active'),
    )


class EnumOption(EnumOptionBase, table=True):
    """DATABASE MODEL for enum options"""
    __tablename__ = "enum_options"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    enum_type_id: uuid.UUID = Field(
        foreign_key="enum_types.id",
        nullable=False,
        index=True
    )
    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    enum_type_obj: Optional[EnumType] = Relationship(back_populates="options")
    preferences: List["DoctorEnumPreference"] = Relationship(back_populates="option")
    
    __table_args__ = (
        sa.Index('idx_enum_option_type_id', 'enum_type_id'),
        sa.Index('idx_enum_option_active', 'is_active'),
        sa.Index('idx_enum_option_type_value', 'enum_type', 'value'),
        sa.Index('idx_enum_option_sort', 'enum_type_id', 'sort_order'),
    )


class DoctorEnumPreference(DoctorEnumPreferenceBase, table=True):
    """DATABASE MODEL for per-doctor enum option toggles"""
    __tablename__ = "doctor_enum_preferences"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    enum_option_id: uuid.UUID = Field(
        foreign_key="enum_options.id",
        nullable=False,
        index=True
    )
    
    # Relationships
    option: Optional[EnumOption] = Relationship(back_populates="preferences")
    
    __table_args__ = (
        sa.Index('idx_doctor_enum_pref_doctor_option', 'doctor_id', 'enum_option_id', unique=True),
        sa.Index('idx_doctor_enum_pref_doctor', 'doctor_id'),
        sa.Index('idx_doctor_enum_pref_option', 'enum_option_id'),
    )


# ============================================================================
# API RESPONSE MODELS (for Swagger/API)
# ============================================================================

class EnumTypePublic(EnumTypeBase):
    """Public enum type response"""
    id: uuid.UUID


class EnumOptionPublic(EnumOptionBase):
    """Public enum option response"""
    id: uuid.UUID
    enum_type_id: uuid.UUID


class DoctorEnumPreferencePublic(DoctorEnumPreferenceBase):
    """Public doctor enum preference response"""
    id: uuid.UUID
    enum_option_id: uuid.UUID


# ============================================================================
# CREATE/UPDATE SCHEMAS
# ============================================================================

class EnumTypeCreate(SQLModel):
    """Schema for creating a new enum type"""
    key: str = Field(max_length=100)
    label: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class EnumTypeUpdate(SQLModel):
    """Schema for updating an enum type"""
    label: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)


class EnumOptionCreate(SQLModel):
    """Schema for creating a new enum option"""
    value: str = Field(max_length=255)
    label: str = Field(max_length=255)
    sort_order: Optional[int] = Field(default=0)


class EnumOptionUpdate(SQLModel):
    """Schema for updating an enum option"""
    label: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)


class EnumOptionToggle(SQLModel):
    """Schema for toggling doctor preference"""
    is_enabled: bool
