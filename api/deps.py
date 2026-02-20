from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlmodel import Session

from core import security
from core.config import settings
from core.db import engine
from models.login_model import TokenPayload
from models.users_model import User
from models.patients_model import Patient
from core.auth_utils import (
    decode_token,
    validate_user_token,
    validate_patient_token,
    AuthenticationError,
    AuthorizationError,
)

# ============================================================================
# SECURITY SCHEMES (displayed in Swagger)
# ============================================================================

# Doctor/Staff/Admin: OAuth2 Password Bearer (role-based, no scopes)
doctor_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    scheme_name="DoctorOAuth2",
    description="OAuth2 password flow for doctors, staff, and admins"
)

# Patient: HTTP Bearer JWT
patient_bearer = HTTPBearer(
    scheme_name="PatientBearer",
    description="JWT Bearer token for patient authentication. Use /login/patient-simple endpoint."
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]

# ============================================================================
# USER/DOCTOR/STAFF/ADMIN AUTHENTICATION (OAuth2)
# ============================================================================

def get_current_user(
    session: SessionDep,
    token: Annotated[str, Depends(doctor_oauth2)]
) -> User:
    """
    Dependency for doctor/staff/admin protected endpoints.
    
    Validates that:
    1. Token is valid JWT signed with SECRET_KEY
    2. Token contains entity='user' (not a patient token)
    3. User ID in token exists in User table
    4. User account is active
    
    Swagger security: DoctorOAuth2
    
    Raises:
        AuthenticationError: Invalid/expired token
        AuthorizationError: Token is not a user/doctor token
        HTTPException(404): User not found
        HTTPException(400): User is inactive
    """
    try:
        payload = decode_token(token)
        user_id, role = validate_user_token(payload)
    except (AuthenticationError, AuthorizationError):
        raise
    except (ValidationError, ValueError) as e:
        raise AuthenticationError(f"Invalid token format: {str(e)}")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


CurrentUser = Annotated[User, Security(get_current_user)]


def get_current_active_superuser(
    current_user: CurrentUser
) -> User:
    """
    Dependency for superuser-only endpoints.
    
    Uses Security() not Depends() - informs Swagger that OAuth2 is required.
    This is CRITICAL for proper Swagger authorization.
    
    Args:
        current_user: Current authenticated user (from get_current_user)
    
    Returns:
        User: Authenticated superuser
        
    Raises:
        HTTPException(403): User is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges"
        )
    return current_user


def require_doctor_role(
    current_user: CurrentUser
) -> User:
    """
    Dependency for doctor-only endpoints.
    
    Uses Security() not Depends() - informs Swagger that OAuth2 is required.
    This is CRITICAL for proper Swagger authorization.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Authenticated doctor
        
    Raises:
        HTTPException(403): User does not have doctor role
    """
    if not current_user.is_doctor:
        raise HTTPException(
            status_code=403,
            detail="Doctor role required"
        )
    return current_user


def require_staff_role(
    current_user: CurrentUser
) -> User:
    """
    Dependency for staff-only endpoints.
    
    Uses Security() not Depends() - informs Swagger that OAuth2 is required.
    This is CRITICAL for proper Swagger authorization.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Authenticated staff member
        
    Raises:
        HTTPException(403): User does not have staff role
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=403,
            detail="Staff role required"
        )
    return current_user


def require_roles(*allowed_roles: str):
    """
    Factory function to create a role-checking dependency.
    
    Allows specifying multiple acceptable roles in a single dependency.
    
    Usage:
        @router.get("/endpoint")
        def my_endpoint(
            current_user: User = Depends(require_roles("doctor", "staff", "admin"))
        ):
            return current_user
    
    Args:
        *allowed_roles: One or more role strings (e.g., "admin", "doctor", "staff")
        
    Returns:
        A dependency function that checks if current_user.role is in allowed_roles
        
    Raises:
        HTTPException(403): User's role not in allowed_roles
    """
    def role_checker(
        current_user: CurrentUser
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges"
            )
        return current_user
    
    return role_checker



# ============================================================================
# PATIENT AUTHENTICATION (JWT Bearer)
# ============================================================================

def get_current_patient(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(patient_bearer)]
) -> Patient:
    """
    Dependency for patient-protected endpoints.
    
    Validates that:
    1. Token is valid JWT signed with SECRET_KEY
    2. Token contains entity='patient' (not a doctor/user token)
    3. Patient ID in token exists in Patient table
    4. Patient account is active
    
    Swagger security: PatientBearer
    
    IMPORTANT: This is COMPLETELY SEPARATE from get_current_user()
    
    Raises:
        AuthenticationError: Invalid/expired token
        AuthorizationError: Token is not a patient token
        HTTPException(404): Patient not found
        HTTPException(400): Patient is inactive
    """
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
        patient_id = validate_patient_token(payload)
    except (AuthenticationError, AuthorizationError):
        raise
    except (ValidationError, ValueError) as e:
        raise AuthenticationError(f"Invalid token format: {str(e)}")

    # Query Patient table, NOT User table
    patient = session.get(Patient, patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient account is inactive",
        )

    return patient


CurrentPatient = Annotated[Patient, Depends(get_current_patient)]


# ============================================================================
# OPTIONAL: Patient role/permission checks
# ============================================================================

def require_patient_ownership(patient: CurrentPatient) -> Patient:
    """
    Verify patient is active and validated.
    
    (Can be extended with additional patient-specific checks)
    """
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account is not active"
        )
    return patient
