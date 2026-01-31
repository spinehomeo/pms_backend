"""
Centralized authentication utilities.

This module contains shared token decoding, validation, and error handling
for both doctor/staff/admin (OAuth2) and patient (JWT Bearer) authentication flows.

Two separate dependency chains ensure:
- Patients query the Patient table
- Doctors/staff/admin query the User table
- No cross-contamination
"""

import jwt
from typing import Optional
from fastapi import HTTPException, status
from pydantic import ValidationError

from core.config import settings
from core.security import ALGORITHM
from models.login_model import TokenPayload


class AuthenticationError(HTTPException):
    """Base authentication error."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization error (user/patient authenticated but lacks permission)."""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def decode_token(token: str) -> dict:
    """
    Safely decode JWT token.
    
    Returns:
        dict: Token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def validate_user_token(payload: dict) -> tuple[str, Optional[str]]:
    """
    Validate token is for a User (doctor/staff/admin).
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        tuple: (user_id, role)
        
    Raises:
        AuthorizationError: If token entity is not 'user' or payload is invalid
    """
    entity = payload.get("entity")
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if entity != "user":
        raise AuthorizationError(
            f"Token is for '{entity}' entity, not 'user'. Use DoctorOAuth2 authentication."
        )
    
    if not user_id:
        raise AuthorizationError("Token missing subject (sub)")
    
    return user_id, role


def validate_patient_token(payload: dict) -> str:
    """
    Validate token is for a Patient.
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        str: Patient ID
        
    Raises:
        AuthorizationError: If token entity is not 'patient' or payload is invalid
    """
    entity = payload.get("entity")
    patient_id = payload.get("sub")
    
    if entity != "patient":
        raise AuthorizationError(
            f"Token is for '{entity}' entity, not 'patient'. Use PatientBearer authentication."
        )
    
    if not patient_id:
        raise AuthorizationError("Token missing subject (sub)")
    
    return patient_id
