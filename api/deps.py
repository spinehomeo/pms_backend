from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlmodel import Session

from core import security
from core.config import settings
from core.db import engine
from models.login_model import TokenPayload
from models.users_model import User
from models.patients_model import Patient

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.DecodeError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_patient(session: SessionDep, token: TokenDep) -> Patient:
    """
    Authentication dependency for patient-protected endpoints.
    
    Validates that:
    1. Token contains entity='patient' (not a user/doctor token)
    2. Patient ID in token exists in Patient table
    3. Patient account is active
    
    This completely separate from get_current_user() to ensure patients
    authenticate from the Patient table, not the User table.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid patient authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )

        entity = payload.get("entity")
        patient_id = payload.get("sub")

        # Verify this is a patient token, not a user/doctor token
        if entity != "patient" or not patient_id:
            raise credentials_exception

    except (jwt.JWTError, jwt.DecodeError, ValidationError):
        raise credentials_exception

    # Query Patient table, not User table
    patient = session.get(Patient, patient_id)

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    if not patient.is_active:
        raise HTTPException(
            status_code=400,
            detail="Patient account is inactive",
        )

    return patient


CurrentPatient = Annotated[Patient, Depends(get_current_patient)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
