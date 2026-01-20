import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import emails  # type: ignore
import jwt
from jwt.exceptions import ExpiredSignatureError, DecodeError

from jinja2 import Template

from core import security
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={
            "project_name": settings.PROJECT_NAME, 
            "email": email_to,
            "app_name": "HomoeoMed"
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "app_name": "HomoeoMed",
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "app_name": "HomoeoMed",
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_email_verification_email(email_to: str, email: str, token: str) -> EmailData:
    """
    Generate email verification email.
    """
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Verify your email address"
    link = f"{settings.FRONTEND_HOST}/verify-email?token={token}"
    html_content = render_email_template(
        template_name="verify_email.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "app_name": "HomoeoMed",
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_welcome_email(email_to: str, username: str) -> EmailData:
    """
    Generate welcome email for new users.
    """
    project_name = settings.PROJECT_NAME
    subject = f"Welcome to {project_name}!"
    html_content = render_email_template(
        template_name="welcome_email.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "app_name": "HomoeoMed",
            "username": username,
            "email": email_to,
            "dashboard_link": f"{settings.FRONTEND_HOST}/dashboard",
            "support_email": settings.SUPPORT_EMAIL,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    """
    Generate password reset token.
    """
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {
            "exp": exp, 
            "nbf": now, 
            "sub": email,
            "type": "password_reset"
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def generate_email_verification_token(email: str) -> str:
    """
    Generate email verification token.
    """
    delta = timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {
            "exp": exp, 
            "nbf": now, 
            "sub": email,
            "type": "email_verification"
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    """
    Verify password reset token.
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        if decoded_token.get("type") != "password_reset":
            return None
        return str(decoded_token["sub"])
    except (DecodeError, ExpiredSignatureError):
        return None


def verify_email_token(token: str) -> str | None:
    """
    Verify email verification token.
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        if decoded_token.get("type") != "email_verification":
            return None
        return str(decoded_token["sub"])
    except (DecodeError, ExpiredSignatureError):
        return None


def generate_appointment_reminder_email(
    email_to: str, 
    patient_name: str, 
    doctor_name: str, 
    appointment_date: str, 
    appointment_time: str
) -> EmailData:
    """
    Generate appointment reminder email.
    """
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Appointment Reminder"
    html_content = render_email_template(
        template_name="appointment_reminder.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "app_name": "HomoeoMed",
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "clinic_link": settings.FRONTEND_HOST,
            "support_email": settings.SUPPORT_EMAIL,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_followup_reminder_email(
    email_to: str, 
    patient_name: str, 
    doctor_name: str, 
    followup_date: str
) -> EmailData:
    """
    Generate follow-up reminder email.
    """
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Follow-up Reminder"
    html_content = render_email_template(
        template_name="followup_reminder.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "app_name": "HomoeoMed",
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "followup_date": followup_date,
            "clinic_link": settings.FRONTEND_HOST,
            "support_email": settings.SUPPORT_EMAIL,
        },
    )
    return EmailData(html_content=html_content, subject=subject)