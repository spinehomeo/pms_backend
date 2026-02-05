from datetime import datetime, timedelta, date, timezone
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils import crud
from utils.time import utc_now, utc_today
from api.deps import CurrentUser, SessionDep, get_current_active_superuser
from core import security
from core.config import settings
from core.security import get_password_hash
from models.login_model import (
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Message,
    Token,
    SessionInfo
)
from models.public_models import PatientLoginRequest, PatientLoginResponse, PatientLoginSimple
from models.users_model import UserPublic, User
from utils.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
    generate_email_verification_token,
    verify_email_token,
    generate_email_verification_email,
)

router = APIRouter(tags=["🔑 Authentication"])

# Basic limiter for auth endpoints (requires slowapi in the environment)
limiter = Limiter(key_func=get_remote_address)


@router.post("/login/access-token")
@limiter.limit("5/minute")
def login_access_token(
    request: Request, session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    elif not user.is_verified:
        raise HTTPException(status_code=400, detail="Email not verified")
    # Check approval status for doctors and staff
    elif user.role in ["doctor", "staff"] and not user.is_approved:
        raise HTTPException(
            status_code=403,
            detail="Your account is pending admin approval. You'll receive an email when approved."
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires, entity="user", role=user.role.value
    )
    
    # Update last login
    user.last_login = utc_today()
    session.add(user)
    session.commit()
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(
    request: Request, session: SessionDep, login_data: LoginRequest
) -> LoginResponse:
    """
    Doctor/Staff/Admin login with email and password
    
    **Credentials:** Email + Password
    **Access Level:** Verified and approved doctors, staff, and administrators
    **Response:** Access token + User details (role, specialization, clinic)
    """
    user = crud.authenticate(
        session=session, email=login_data.email, password=login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password. Please verify your credentials."
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Your account is inactive. Contact the administrator."
        )
    elif not user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Email not verified. Please check your inbox for verification link."
        )
    # Check approval status for doctors and staff
    elif user.role in ["doctor", "staff"] and not user.is_approved:
        raise HTTPException(
            status_code=403,
            detail="Your account is pending admin approval. You'll receive an email when approved."
        )
    
    if login_data.remember_me:
        access_token_expires = timedelta(days=30)
    else:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires, entity="user", role=user.role.value
    )
    
    # Update last login
    user.last_login = utc_today()
    session.add(user)
    session.commit()
    
    user_data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_verified": user.is_verified,
        "is_superuser": user.is_superuser,
        "specialization": user.specialization,
        "clinic_name": user.clinic_name,
    }
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=access_token_expires.total_seconds(),
        user=user_data
    )


# COMMENTED OUT - Using simplified patient login instead
# @router.post("/login/patient", response_model=PatientLoginResponse, tags=["login-patient"])
# @limiter.limit("5/minute")
# def login_patient(
#     request: Request, session: SessionDep, login_data: PatientLoginRequest
# ) -> PatientLoginResponse:
#     """
#     Patient login with phone number and password (PUBLIC ENDPOINT)
#     
#     **Credentials:** Phone number + Password
#     **Authentication:** Not required - public endpoint
#     **Access Level:** Patients with active accounts
#     **Response:** Access token + Patient details (age, gender, doctor info)
#     """
#     patient = crud.authenticate_patient(
#         session=session, phone=login_data.phone, password=login_data.password
#     )
#     if not patient:
#         raise HTTPException(
#             status_code=400,
#             detail="Incorrect phone number or password. Please verify your credentials."
#         )
#     elif not patient.is_active:
#         raise HTTPException(
#             status_code=400,
#             detail="Your patient account is inactive. Please contact your doctor."
#         )
#     
#     if login_data.remember_me:
#         access_token_expires = timedelta(days=30)
#     else:
#         access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#     
#     access_token = security.create_access_token(
#         patient.id, expires_delta=access_token_expires
#     )
#     
#     # Update last login
#     patient.last_login = datetime.now().date()
#     session.add(patient)
#     session.commit()
#     
#     patient_data = {
#         "id": str(patient.id),
#         "full_name": patient.full_name,
#         "phone": patient.phone,
#         "email": patient.email,
#         "gender": patient.gender,
#         "age": patient.age,
#         "doctor_id": str(patient.doctor_id),
#     }
#     
#     return PatientLoginResponse(
#         access_token=access_token,
#         token_type="bearer",
#         expires_in=int(access_token_expires.total_seconds()),
#         patient=patient_data
#     )


@router.post("/login/patient-simple", response_model=PatientLoginResponse)
@limiter.limit("5/minute")
def login_patient_simple(
    request: Request, session: SessionDep, login_data: PatientLoginSimple
) -> PatientLoginResponse:
    """
    Simplified patient login with name and phone only (PUBLIC ENDPOINT)
    
    **Credentials:** Full name + Phone number
    **Password:** Phone number is used as default password
    **Authentication:** Not required - public endpoint
    **Access Level:** Registered patients
    **Response:** Access token + Patient details
    """
    # Find patient by phone and full_name match
    from sqlmodel import select
    from models.patients_model import Patient
    
    patient = session.exec(
        select(Patient).where(
            Patient.phone == login_data.phone,
            Patient.full_name == login_data.full_name
        )
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=400,
            detail="Patient not found. Please verify your name and phone number."
        )
    elif not patient.is_active:
        raise HTTPException(
            status_code=400,
            detail="Your patient account is inactive. Please contact your doctor."
        )
    
    # Use phone as password for authentication
    from core.security import verify_password
    phone_as_password = login_data.phone
    
    if not patient.hashed_password:
        # First time login - set password to phone number
        patient.hashed_password = get_password_hash(phone_as_password)
        session.add(patient)
        session.commit()
    else:
        # Verify phone as password
        if not verify_password(phone_as_password, patient.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Invalid credentials. Phone number mismatch."
            )
    
    # Generate token
    access_token_expires = timedelta(days=30)  # Default longer expiry for simplified login
    access_token = security.create_access_token(
        patient.id, expires_delta=access_token_expires, entity="patient", role="patient"
    )
    
    # Update last login
    patient.last_login = utc_today()
    session.add(patient)
    session.commit()
    
    patient_data = {
        "id": str(patient.id),
        "full_name": patient.full_name,
        "phone": patient.phone,
        "email": patient.email,
        "gender": patient.gender,
        "age": patient.age,
        "doctor_id": str(patient.doctor_id),
    }
    
    return PatientLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        patient=patient_data
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery")
def recover_password(forgot_data: ForgotPasswordRequest, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=forgot_data.email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    password_reset_token = generate_password_reset_token(email=forgot_data.email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=user.email, token=password_reset_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


@router.post("/reset-password/")
def reset_password(session: SessionDep, reset_data: ResetPasswordRequest) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=reset_data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    hashed_password = get_password_hash(password=reset_data.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    
    return Message(message="Password updated successfully")


@router.post("/verify-email/{token}")
def verify_email(token: str, session: SessionDep) -> Message:
    """
    Verify email address
    """
    email = verify_email_token(token=token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    
    if user.is_verified:
        return Message(message="Email already verified")
    
    user.is_verified = True
    session.add(user)
    session.commit()
    
    return Message(message="Email verified successfully")


@router.post("/resend-verification")
def resend_verification(email: str, session: SessionDep) -> Message:
    """
    Resend email verification
    """
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    
    if user.is_verified:
        return Message(message="Email already verified")
    
    verification_token = generate_email_verification_token(email=email)
    email_data = generate_email_verification_email(
        email_to=user.email, email=user.email, token=verification_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message="Verification email sent")


@router.get("/session", response_model=SessionInfo)
def get_session_info(current_user: CurrentUser) -> SessionInfo:
    """
    Get current session information
    """
    return SessionInfo(
        user_id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        last_login=current_user.last_login,
        session_start=utc_now()
    )


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )