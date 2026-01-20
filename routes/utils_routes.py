from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic.networks import EmailStr

from api.deps import get_current_active_superuser
from models.login_model import Message
from utils.utils import (
    generate_test_email, 
    generate_email_verification_email, 
    send_email, 
    generate_email_verification_token
)

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
    response_model=Message
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.post(
    "/send-verification-email/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message
)
def send_verification_email(email_to: EmailStr) -> Message:
    """
    Send verification email to a user.
    """
    verification_token = generate_email_verification_token(email=email_to)
    email_data = generate_email_verification_email(
        email_to=email_to, email=email_to, token=verification_token
    )
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Verification email sent")


@router.get("/health-check/")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.
    """
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "HomoeoMed API"
    }


@router.get("/system-info/")
async def system_info(current_user: Any = Depends(get_current_active_superuser)) -> dict[str, Any]:
    """
    Get system information (admin only).
    """
    import platform
    import sys
    from datetime import datetime
    
    return {
        "system": platform.system(),
        "python_version": sys.version,
        "timestamp": datetime.now().isoformat(),
        "api_version": "1.0.0",
        "environment": "production" if not settings.DEBUG else "development"
    }