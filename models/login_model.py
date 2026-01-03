from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Field, SQLModel
from pydantic import BaseModel


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None


class LoginRequest(SQLModel):
    """API INPUT MODEL for login"""
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = Field(default=False)


class LoginResponse(SQLModel):
    """API OUTPUT MODEL for login"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: Dict[str, Any]


class ForgotPasswordRequest(SQLModel):
    """API INPUT MODEL for forgot password"""
    email: str = Field(max_length=255)


class ResetPasswordRequest(SQLModel):
    """API INPUT MODEL for resetting password"""
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetResponse(SQLModel):
    """API OUTPUT MODEL for password reset"""
    message: str
    reset_at: datetime


class VerifyEmailRequest(SQLModel):
    """API INPUT MODEL for email verification"""
    token: str


class SessionInfo(SQLModel):
    """API OUTPUT MODEL for session information"""
    user_id: str
    email: str
    full_name: str
    role: str
    last_login: Optional[datetime] = None
    session_start: datetime = Field(default_factory=datetime.now)