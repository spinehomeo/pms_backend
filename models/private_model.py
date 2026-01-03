from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel
from pydantic import EmailStr


class PrivateUserCreate(SQLModel):
    """PRIVATE MODEL for creating users (admin/internal use)"""
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)
    role: str = Field(default="doctor")
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    is_verified: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    join_date: date = Field(default_factory=date.today)


class PrivateUserUpdate(SQLModel):
    """PRIVATE MODEL for updating users (admin/internal use)"""
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_active: Optional[bool] = None