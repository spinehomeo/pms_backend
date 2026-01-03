from datetime import datetime, timedelta
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils import crud
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

router = APIRouter(tags=["login"])

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
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Update last login
    user.last_login = datetime.now().date()
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
    Login with email and password
    """
    user = crud.authenticate(
        session=session, email=login_data.email, password=login_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    elif not user.is_verified:
        raise HTTPException(status_code=400, detail="Email not verified")
    
    if login_data.remember_me:
        access_token_expires = timedelta(days=30)
    else:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Update last login
    user.last_login = datetime.now().date()
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
        session_start=datetime.now()
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