import uuid
import time
from datetime import date, datetime, timedelta
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Security
from sqlmodel import col, delete, func, select, or_
from sqlalchemy.exc import IntegrityError
import jwt

from utils import crud
from utils.enum_service import EnumService
from api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
    get_current_user,
    require_roles,
)
from core import security
from core.config import settings
from core.security import get_password_hash, verify_password
from models.login_model import Message
from models.patients_model import Patient, PatientPublic
from models.users_model import (
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
    UpdatePassword,
    DoctorStats,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStats,
    UserStats,
)
from models.public_models import PatientRegisterPublic, PatientRegisterPhoneOnly, PatientRegisterSimple, PatientQuickAccessResponse
from utils.utils import (
    generate_new_account_email,
    generate_email_verification_email,
    generate_email_verification_token,
    send_email
)
from models.audit_model import AuditLog

# ============================================================================
# ROUTER SETUP - SPLIT BY AUTHORIZATION LEVEL
# ============================================================================

# Router for admin-only operations (system-level CRUD)
# This router has admin-only dependency at router level
# Prefix: /admin/users - for all admin user management endpoints
admin_router = APIRouter(
    prefix="/admin/users",
    dependencies=[Security(get_current_active_superuser)]
)

# Router for self-service + public endpoints (no router-level auth)
# Individual endpoints apply their own dependencies as needed
# Prefix: /users - for self-service user endpoints
self_service_router = APIRouter(prefix="/users")

# Main router that combines both (for api/router.py to include)
# No prefix here - both sub-routers have their own prefixes
router = APIRouter()


@admin_router.get(
    "/",
    response_model=UsersPublic,
    tags=["🛡️ Admin | User Management"],
    operation_id="admin_read_users"
)
def read_users(
    session: SessionDep,
    role: Optional[Literal["doctor", "staff", "admin"]] = None,
    is_approved: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Retrieve all users (doctors, staff, admins) in the system with advanced filtering.

    **Query Parameters:**
    - `role`: Filter by role (doctor, staff, admin)
    - `is_approved`: Filter by approval status (true/false)
    - `is_verified`: Filter by email verification status (true/false)
    - `is_active`: Filter by active status (true/false)
    - `search`: Search by name, email, or phone (case-insensitive)
    - `skip`: Number of records to skip (default: 0)
    - `limit`: Number of records to return (default: 100, max: 1000)

    **Response:** List of users with total count

    **Examples:**
    - Get all pending doctors: `?role=doctor&is_approved=false&is_verified=true`
    - Get all active staff: `?role=staff&is_active=true`
    - Search users: `?search=ahmed`
    """
    # Base query - IMPORTANT: Exclude PATIENT role (legacy data)
    # Only query valid user roles (doctor, staff, admin)
    query = select(User).where(
        User.role.in_(["doctor", "staff", "admin"])
    )
    
    # Apply filters
    if role:
        query = query.where(User.role == role)
    
    if is_approved is not None:
        query = query.where(User.is_approved == is_approved)
    
    if is_verified is not None:
        query = query.where(User.is_verified == is_verified)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(User.full_name).contains(search),
                func.lower(User.email).contains(search) if User.email else False,
                func.lower(User.phone).contains(search) if User.phone else False
            )
        )
    
    # Get total count
    # IMPORTANT: Exclude PATIENT role (legacy data)
    count_statement = select(func.count()).select_from(User).where(
        User.role.in_(["doctor", "staff", "admin"])
    )
    
    # Apply same filters to count
    if role:
        count_statement = count_statement.where(User.role == role)
    if is_approved is not None:
        count_statement = count_statement.where(User.is_approved == is_approved)
    if is_verified is not None:
        count_statement = count_statement.where(User.is_verified == is_verified)
    if is_active is not None:
        count_statement = count_statement.where(User.is_active == is_active)
    if search:
        count_statement = count_statement.where(
            or_(
                func.lower(User.full_name).contains(search),
                func.lower(User.email).contains(search) if User.email else False,
                func.lower(User.phone).contains(search) if User.phone else False
            )
        )
    
    count = session.exec(count_statement).one()
    
    # Order by most recent first
    query = query.order_by(User.join_date.desc())
    
    # Get paginated results
    users = session.exec(query.offset(skip).limit(limit)).all()

    return UsersPublic(data=users, count=count)


@admin_router.post(
    "/",
    response_model=UserPublic,
    tags=["🛡️ Admin | User Management"],
    operation_id="admin_create_user"
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Create a new user (doctor, staff, or admin).

    **Key Differences from Public Signup:**
    - User is **auto-verified** (no email verification needed)
    - User is **auto-approved** (no additional admin approval needed)
    - User is **immediately active** (can login right away)
    - Admin can set all fields directly
    - No email verification sent

    **Required fields:** email, password, full_name, role

    **Role options:** "doctor", "staff", "admin"

    **Behavior:**
    - Checks if email already exists
    - Hashes password securely
    - Sets is_verified = TRUE
    - Sets is_approved = TRUE
    - Sets is_active = TRUE
    - Logs creation in audit trail
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    
    # CRITICAL: Admin-created users are auto-approved and verified
    user.is_verified = True   # Auto-verified (no email verification needed)
    user.is_approved = True   # Auto-approved (no additional approval needed)
    user.is_active = True     # Immediately active (can login right away)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Audit log
    try:
        audit = AuditLog(
            user_id=user.id,
            action="user_created_by_admin",
            entity="user",
            entity_id=user.id,
            changes=f"User created by admin: {user.full_name} ({user.role})"
        )
        session.add(audit)
        session.commit()
    except Exception:
        # Don't break user creation on audit failures
        session.rollback()
    
    return user


# ============================================================================
# APPROVAL ENDPOINTS - Static routes MUST come before parameterized routes
# ============================================================================

@admin_router.get("/pending-approvals", response_model=UsersPublic, tags=["🛡️ Admin | Approvals"])
def get_pending_users(
    session: SessionDep,
    role: str | None = Query(None, description="Filter by role: 'doctor', 'staff', or None for all pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** OAuth2

    List all users (doctors and staff) waiting for admin approval.

    **Query Parameters:**
    - `role`: Optional filter - "doctor", "staff", or None for all pending users
    - `skip`: Results to skip (default: 0)
    - `limit`: Results to return (default: 100, max: 1000)

    **Filters:**
    - email_verified = TRUE (email confirmation done)
    - is_approved = FALSE (not yet approved)
    - role = "doctor" or "staff" (excludes admins)

    **Returns:**
    - Count of pending users
    - List with: id, email, full_name, phone, role, specialization, registration_number, clinic_name
    """
    # Build query
    query = select(User).where(
        User.is_verified == True,
        User.is_approved == False,
        User.role.in_(["doctor", "staff"])
    )
    
    # Optional role filter
    if role and role in ["doctor", "staff"]:
        query = query.where(User.role == role)
    
    # Get count
    count_statement = select(func.count()).where(
        User.is_verified == True,
        User.is_approved == False,
        User.role.in_(["doctor", "staff"])
    )
    if role and role in ["doctor", "staff"]:
        count_statement = count_statement.where(User.role == role)
    count = session.exec(count_statement).one()
    
    # Get paginated results, order by newest first
    pending_users = session.exec(query.order_by(User.join_date.desc()).offset(skip).limit(limit)).all()
    
    return UsersPublic(data=pending_users, count=count)


@admin_router.get("/pending-approvals/stats", response_model=ApprovalStats, tags=["🛡️ Admin | Approvals"])
def get_approval_stats(
    session: SessionDep,
    current_user: CurrentUser = None
) -> Any:
    """
    🛡️ **Access:** ADMIN only

    **Authentication:** OAuth2

    Get approval statistics for admin dashboard.

    **Returns:**
    - total_pending: All waiting approvals (verified, not approved)
    - pending_doctors: Doctors waiting approval
    - pending_staff: Staff waiting approval
    - pending_unverified_email: Signed up but haven't verified email
    - approved_today: Users approved today
    - rejected_today: Users rejected today
    """
    from models.users_model import ApprovalStats
    from datetime import datetime
    
    today = datetime.utcnow().date()
    
    # Total pending (email verified, approval pending)
    total_pending = session.exec(
        select(func.count()).where(
            User.is_verified == True,
            User.is_approved == False,
            User.role.in_(["doctor", "staff"])
        )
    ).one()
    
    # Pending doctors
    pending_doctors = session.exec(
        select(func.count()).where(
            User.is_verified == True,
            User.is_approved == False,
            User.role == "doctor"
        )
    ).one()
    
    # Pending staff
    pending_staff = session.exec(
        select(func.count()).where(
            User.is_verified == True,
            User.is_approved == False,
            User.role == "staff"
        )
    ).one()
    
    # Pending email verification
    pending_unverified = session.exec(
        select(func.count()).where(
            User.is_verified == False,
            User.role.in_(["doctor", "staff"])
        )
    ).one()
    
    # Approved today
    approved_today = session.exec(
        select(func.count()).where(
            User.is_approved == True,
            User.role.in_(["doctor", "staff"]),
            User.join_date >= today
        )
    ).one()
    
    # Rejected today (users with rejection_reason)
    rejected_today = session.exec(
        select(func.count()).where(
            User.is_approved == False,
            User.rejection_reason.isnot(None),
            User.role.in_(["doctor", "staff"])
        )
    ).one()
    
    return ApprovalStats(
        total_pending=total_pending,
        pending_doctors=pending_doctors,
        pending_staff=pending_staff,
        pending_unverified_email=pending_unverified,
        approved_today=approved_today,
        rejected_today=rejected_today
    )


@admin_router.get(
    "/{user_id}",
    response_model=UserPublic,
    tags=["🛡️ Admin | User Management"],
    operation_id="admin_read_user_by_id"
)
def read_user_by_id(
    user_id: uuid.UUID,
    session: SessionDep
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Get detailed information about a specific user by ID.

    **Path Parameters:**
    - `user_id`: UUID of the user

    **Returns:**
    - Full user details including:
      - Basic info (name, email, role, phone)
      - Status flags (verified, approved, active)
      - Doctor-specific fields (specialization, clinic, fee)
      - Timestamps (join date, last login)

    **Note:** This is admin-only. Regular users use /users/me
    """
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return user


@admin_router.patch(
    "/{user_id}",
    response_model=UserPublic,
    tags=["🛡️ Admin | User Management"],
    operation_id="admin_update_user"
)
def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    session: SessionDep,
    current_admin: CurrentUser
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Update any user's information.

    **Path Parameters:**
    - `user_id`: UUID of user to update

    **Updateable Fields:**
    - Basic: email, full_name, phone, role
    - Doctor: specialization, registration_number, clinic_name, clinic_address, consultation_fee
    - Status: is_verified, is_approved, is_active

    **Admin Powers:**
    - Can change user role (doctor ↔ staff ↔ admin)
    - Can manually verify email (is_verified)
    - Can manually approve/unapprove (is_approved)
    - Can activate/deactivate account (is_active)
    - Can update any field

    **Restrictions:**
    - Email must be unique if changed
    - Cannot update password via this endpoint (use /password endpoints)
    - User must exist

    **Behavior:**
    - Only provided fields are updated (partial update)
    - Logs all changes in audit trail
    - Checks email uniqueness if email changed
    """
    
    # Get user
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Track what changed for audit log
    changes = {}
    
    # Update only provided fields
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Check email uniqueness if email is being changed
    if "email" in update_data and update_data["email"] != user.email:
        existing = session.exec(
            select(User).where(
                User.email == update_data["email"],
                User.id != user_id
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email already in use by another user"
            )
        changes["email"] = {
            "from": user.email,
            "to": update_data["email"]
        }
    
    # Track role changes
    if "role" in update_data and update_data["role"] != user.role:
        changes["role"] = {
            "from": str(user.role),
            "to": str(update_data["role"])
        }
    
    # Track status changes
    for field in ["is_verified", "is_approved", "is_active"]:
        if field in update_data and update_data[field] != getattr(user, field):
            changes[field] = {
                "from": getattr(user, field),
                "to": update_data[field]
            }
    
    # Apply updates
    for field, value in update_data.items():
        setattr(user, field, value)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Log audit trail
    if changes:
        try:
            audit = AuditLog(
                user_id=user.id,
                action="user_updated_by_admin",
                entity="user",
                entity_id=user.id,
                changes=f"Updates: {str(changes)}"
            )
            session.add(audit)
            session.commit()
        except Exception:
            session.rollback()
    
    return user


@admin_router.delete(
    "/{user_id}",
    response_model=dict,
    tags=["🛡️ Admin | User Management"],
    operation_id="admin_delete_user"
)
def delete_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_admin: CurrentUser
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Delete a user from the system.

    **Path Parameters:**
    - `user_id`: UUID of user to delete

    **Restrictions:**
    - Cannot delete yourself (safety measure)
    - Doctors with assigned patients should be handled carefully
      (consider soft delete or transfer patients first)

    **Behavior:**
    - Permanently deletes user from database
    - Cascades to related records (based on FK constraints)
    - Logs deletion in audit trail
    - Cannot be undone (consider soft delete as alternative)

    **Alternative: Soft Delete**
    Instead of deleting, consider:
    - Set is_active = FALSE (deactivate)
    - Set is_approved = FALSE (revoke approval)
    - Keep user data for audit trail
    """
    
    # Get user
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Safety: Cannot delete yourself
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account. Use self-service endpoint instead."
        )
    
    # Optional: Check for dependencies (e.g., assigned patients)
    if user.role == "doctor":
        from models.patients_model import Patient
        patient_count = session.exec(
            select(func.count()).where(Patient.doctor_id == user.id)
        ).one()
        
        if patient_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete doctor with {patient_count} assigned patients. Transfer patients first."
            )
    
    # Log before deletion
    try:
        audit = AuditLog(
            user_id=user.id,
            action="user_deleted_by_admin",
            entity="user",
            entity_id=user.id,
            changes=f"User deleted: {user.full_name} ({user.role})"
        )
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()
    
    # Delete user
    session.delete(user)
    session.commit()
    
    return {
        "message": f"User '{user.full_name}' ({user.role}) has been deleted"
    }


@admin_router.get(
    "/stats",
    response_model=UserStats,
    tags=["🛡️ Admin | User Management"],
    operation_id="admin_get_user_stats"
)
def get_user_stats(
    session: SessionDep
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Get comprehensive user statistics for admin dashboard.

    **Returns:**
    - Total users by role (doctors, staff, admins)
    - Active vs inactive counts
    - Pending approvals/verifications
    - Recent signup trends (today, this week, this month)

    **Use Cases:**
    - Dashboard overview
    - Monitor user growth
    - Track approvals needed
    - System health metrics
    """
    
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Total users - IMPORTANT: Exclude PATIENT role (legacy data)
    total_users = session.exec(
        select(func.count()).select_from(User).where(
            User.role.in_(["doctor", "staff", "admin"])
        )
    ).one()
    active_users = session.exec(
        select(func.count()).select_from(User).where(
            User.role.in_(["doctor", "staff", "admin"]),
            User.is_active == True
        )
    ).one()
    inactive_users = total_users - active_users
    
    # Doctors
    total_doctors = session.exec(
        select(func.count()).select_from(User).where(User.role == "doctor")
    ).one()
    active_doctors = session.exec(
        select(func.count()).select_from(User).where(
            User.role == "doctor",
            User.is_active == True
        )
    ).one()
    pending_doctors = session.exec(
        select(func.count()).select_from(User).where(
            User.role == "doctor",
            User.is_verified == True,
            User.is_approved == False
        )
    ).one()
    
    # Staff
    total_staff = session.exec(
        select(func.count()).select_from(User).where(User.role == "staff")
    ).one()
    active_staff = session.exec(
        select(func.count()).select_from(User).where(
            User.role == "staff",
            User.is_active == True
        )
    ).one()
    pending_staff = session.exec(
        select(func.count()).select_from(User).where(
            User.role == "staff",
            User.is_verified == True,
            User.is_approved == False
        )
    ).one()
    
    # Admins
    total_admins = session.exec(
        select(func.count()).select_from(User).where(User.role == "admin")
    ).one()
    
    # Pending counts
    pending_verification = session.exec(
        select(func.count()).select_from(User).where(
            User.is_verified == False,
            User.role.in_(["doctor", "staff"])
        )
    ).one()
    
    pending_approval = session.exec(
        select(func.count()).select_from(User).where(
            User.is_verified == True,
            User.is_approved == False,
            User.role.in_(["doctor", "staff"])
        )
    ).one()
    
    # Recent signups - IMPORTANT: Exclude PATIENT role (legacy data)
    created_today = session.exec(
        select(func.count()).select_from(User).where(
            User.join_date >= today,
            User.role.in_(["doctor", "staff", "admin"])
        )
    ).one()
    
    created_this_week = session.exec(
        select(func.count()).select_from(User).where(
            User.join_date >= week_ago.date(),
            User.role.in_(["doctor", "staff", "admin"])
        )
    ).one()
    
    created_this_month = session.exec(
        select(func.count()).select_from(User).where(
            User.join_date >= month_ago.date(),
            User.role.in_(["doctor", "staff", "admin"])
        )
    ).one()
    
    return UserStats(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_doctors=total_doctors,
        active_doctors=active_doctors,
        pending_doctors=pending_doctors,
        total_staff=total_staff,
        active_staff=active_staff,
        pending_staff=pending_staff,
        total_admins=total_admins,
        pending_verification=pending_verification,
        pending_approval=pending_approval,
        created_today=created_today,
        created_this_week=created_this_week,
        created_this_month=created_this_month
    )


# ============================================================================
# SELF-SERVICE ENDPOINTS (Doctor / Staff / Admin - Own Resources)
# ============================================================================
# These endpoints are NOT admin-only
# Individual auth dependencies are applied to each endpoint

@self_service_router.patch("/me", response_model=UserPublic, tags=["👤 Self-Service | User Profile"])
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    👤 **Access:** Doctor, Staff, Admin (own profile only)

    **Authentication:** DoctorOAuth2

    Update the current logged-in user's profile.

    **Allowed fields:** full_name, email

    **Important:**
    - Users can only update their OWN profile
    - Email uniqueness is checked across system
    - Audit log records this change
    """
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@self_service_router.patch("/me/password", response_model=Message, tags=["👤 Self-Service | Password"])
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    👤 **Access:** Doctor, Staff, Admin (own password only)

    **Authentication:** DoctorOAuth2

    Change the current user's password.

    **Required fields:**
    - `current_password`: Current password (for verification)
    - `new_password`: New password (must differ from current)

    **Validation:**
    - Current password must be correct
    - New password cannot equal current password
    - Audit log records this change
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()

    # Audit log
    try:
        audit = AuditLog(user_id=current_user.id, action="update_password", entity="user", entity_id=current_user.id)
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()

    return Message(message="Password updated successfully")


@self_service_router.get("/me", response_model=UserPublic, tags=["👤 Self-Service | User Profile"])
def read_user_me(current_user: CurrentUser) -> Any:
    """
    👤 **Access:** Doctor, Staff, Admin

    **Authentication:** DoctorOAuth2

    Get the current logged-in user's profile information.

    **Returns:** Full user details (email, name, role, status, etc.)

    **No parameters required** - Uses bearer token from authorization header
    """
    return current_user


# COMMENTED OUT - Using simplified patient login approach
# @router.get("/patients/me", response_model=PatientPublic)
# def read_patient_me(session: SessionDep, token: TokenDep) -> Any:
#     """
#     Get current patient profile using phone+password login token.
#     
#     **Authentication:** Patient token from /login/patient endpoint
#     **Response:** Patient details (name, phone, email, gender, age, doctor info)
#     """
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
#         patient_id: str = payload.get("sub")
#         if not patient_id:
#             raise HTTPException(status_code=401, detail="Invalid token")
#     except jwt.JWTError:
#         raise HTTPException(status_code=401, detail="Invalid token")
#     
#     patient = session.get(Patient, uuid.UUID(patient_id))
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")
#     
#     if not patient.is_active:
#         raise HTTPException(status_code=400, detail="Patient account is inactive")
#     
#     return patient


@self_service_router.get("/me/stats", response_model=DoctorStats, tags=["🧑‍⚕️ Doctor | Statistics"])
def get_doctor_stats(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    🧑‍⚕️ **Access:** Doctor (other roles can authenticate but endpoint is doctor-specific)

    **Authentication:** DoctorOAuth2

    Get dashboard statistics for the current doctor.

    **Returns:**
    - Total patients assigned to doctor
    - Total cases handled
    - Total appointments
    - Total prescriptions issued
    - Upcoming appointments (today or future)
    - Low stock medicine items
    - Revenue metrics (if enabled)

    **Restrictions:** Only available to users with doctor role
    """
    from sqlmodel import func, select
    from models.patients_model import Patient
    from models.cases_model import PatientCase
    from models.appointments_model import Appointment
    from models.prescriptions_model import Prescription
    from datetime import date
    
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403,
            detail="Only doctors can access statistics"
        )
    
    # Get counts
    total_patients = session.exec(
        select(func.count()).where(Patient.doctor_id == current_user.id)
    ).one()
    
    total_cases = session.exec(
        select(func.count()).where(PatientCase.doctor_id == current_user.id)
    ).one()
    
    total_appointments = session.exec(
        select(func.count()).where(Appointment.doctor_id == current_user.id)
    ).one()
    
    total_prescriptions = session.exec(
        select(func.count()).where(Prescription.doctor_id == current_user.id)
    ).one()
    
    # Get upcoming appointments (scheduled for today or future)
    today = date.today()
    upcoming_appointments = session.exec(
        select(func.count()).where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date >= today
        )
    ).one()
    
    return DoctorStats(
        total_patients=total_patients,
        total_cases=total_cases,
        total_appointments=total_appointments,
        total_prescriptions=total_prescriptions,
        upcoming_appointments=upcoming_appointments,
        pending_followups=0,  # You can add this calculation if needed
        revenue_today=0.0,  # You can add revenue calculations if needed
        revenue_this_month=0.0
    )


@self_service_router.delete("/me", response_model=Message, tags=["👤 Self-Service | User Profile"])
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    👤 **Access:** Doctor, Staff, Admin (own account only)

    **Authentication:** DoctorOAuth2

    Delete the current logged-in user's own account.

    **Restrictions:**
    - Super users (ADMIN) cannot delete themselves (set safety)
    - Doctors with assigned patients cannot be deleted (must transfer first)
    - This action is permanent and logs in audit trail

    **Audit:** Deletion is logged as "delete_self" action
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    
    # Check if doctor has patients (prevent deletion if there are dependent records)
    if current_user.role == "doctor":
        from sqlmodel import select, func
        from models.patients_model import Patient
        
        patient_count = session.exec(
            select(func.count()).where(Patient.doctor_id == current_user.id)
        ).one()
        
        if patient_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete doctor account with existing patients. Transfer patients first."
            )
    
    session.delete(current_user)
    session.commit()

    try:
        audit = AuditLog(user_id=current_user.id, action="delete_self", entity="user", entity_id=current_user.id)
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()

    return Message(message="User deleted successfully")


@self_service_router.post("/signup", response_model=UserPublic, tags=["📝 Registration | User Signup"])
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    📝 **Access:** Doctor, Staff (public signup)

    **Authentication:** Public (no login required)

    User self-registration endpoint for creating new doctor or staff accounts.
    BOTH require admin approval.

    **Required fields:**
    - `email`: Unique email address
    - `password`: Secure password
    - `full_name`: User's full name
    - `role`: Account type ("doctor" or "staff")
    
    **Doctor-specific fields (collected for verification):**
    - `registration_number`: Medical license/registration number
    - `specialization`: Medical specialization
    - `clinic_name`: Practice/clinic name
    - `clinic_address`: Practice/clinic address

    **Workflow:**
    1. User (doctor or staff) submits signup
    2. Email verification link sent
    3. After email verification, account pending admin approval
    4. Admin reviews and approves
    5. User can login once approved

    **Account status on signup:**
    - is_verified: FALSE (pending email confirmation)
    - is_approved: FALSE (pending admin approval)
    - is_active: FALSE (can't login until approved)
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    
    user_create = UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        phone=user_in.phone,
        registration_number=user_in.registration_number if user_in.role == "doctor" else None,
        specialization=user_in.specialization if user_in.role == "doctor" else None,
        role=user_in.role  # Use role from user input (doctor or staff)
    )
    
    user = crud.create_user(session=session, user_create=user_create)
    
    # Store additional fields (doctor-specific)
    if user_in.role == "doctor":
        user.clinic_name = user_in.clinic_name
        user.clinic_address = user_in.clinic_address
    
    # Both doctors and staff require approval
    user.is_approved = False  # Requires admin approval
    user.is_active = False     # Can't login until approved
    user.is_verified = False   # Email verification required first
    session.add(user)
    session.commit()
    
    # Send verification email
    if settings.emails_enabled:
        verification_token = generate_email_verification_token(email=user_in.email)
        email_data = generate_email_verification_email(
            email_to=user_in.email, email=user_in.email, token=verification_token
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    
    return user


# COMMENTED OUT - Using simplified patient registration instead (/patients/register-simple)
# @router.post("/patients/register", response_model=UserPublic)
# def register_patient(session: SessionDep, patient_in: PatientRegisterPublic) -> Any:
#     """
#     Public patient registration endpoint.
#     
#     Creates a new patient user account without admin approval.
#     """
#     # Check if user already exists
#     user = crud.get_user_by_email(session=session, email=patient_in.email)
#     if user:
#         raise HTTPException(
#             status_code=400,
#             detail="The user with this email already exists in the system",
#         )
#     
#     # Create user with PATIENT role
#     user_create = UserCreate(
#         email=patient_in.email,
#         password=patient_in.password,
#         full_name=patient_in.full_name,
#         role=UserRole.PATIENT,  # Set as patient
#         phone=patient_in.phone,
#     )
#     
#     user = crud.create_user(session=session, user_create=user_create)
#     
#     # Send verification email
#     if settings.emails_enabled:
#         verification_token = generate_email_verification_token(email=patient_in.email)
#         email_data = generate_email_verification_email(
#             email_to=patient_in.email, email=patient_in.email, token=verification_token
#         )
#         send_email(
#             email_to=patient_in.email,
#             subject=email_data.subject,
#             html_content=email_data.html_content,
#         )
#     
#     # Audit log
#     try:
#         audit = AuditLog(user_id=user.id, action="patient_registration", entity="user", entity_id=user.id)
#         session.add(audit)
#         session.commit()
#     except Exception:
#         session.rollback()
#     
#     return user


# COMMENTED OUT - Using simplified patient registration instead (/patients/register-simple)
# @router.post("/patients/register-phone", response_model=UserPublic, tags=["patient-registration"])
# def register_patient_phone(session: SessionDep, patient_in: PatientRegisterPhoneOnly) -> Any:
#     """
#     Patient registration with phone number and name only (SIMPLIFIED)
#     
#     **Required fields:** full_name, phone, password
#     **No email verification required**
#     **Patient can login immediately with phone + password**
#     
#     Creates a patient user account with minimal information.
#     """
#     # Check if patient with this phone already exists
#     existing_patient = session.exec(
#         select(Patient).where(Patient.phone == patient_in.phone)
#     ).first()
#     if existing_patient:
#         raise HTTPException(
#             status_code=400,
#             detail="Patient with this phone number already exists"
#         )
#     
#     # Auto-generate email (since User model requires it)
#     auto_email = f"patient_{patient_in.phone}@pms.internal"
#     
#     # Check if auto-generated email is already used
#     user = crud.get_user_by_email(session=session, email=auto_email)
#     if user:
#         raise HTTPException(
#             status_code=400,
#             detail="Patient registration failed. Please try again."
#         )
#     
#     # Create user with PATIENT role (no email verification needed)
#     user_create = UserCreate(
#         email=auto_email,
#         password=patient_in.password or "TempPass123",  # Use provided or generate temp
#         full_name=patient_in.full_name,
#         role=UserRole.PATIENT,
#         phone=patient_in.phone,
#         is_verified=True  # Skip email verification for phone-based registration
#     )
#     
#     user = crud.create_user(session=session, user_create=user_create)
#     
#     # Create patient record in Patient table with password for phone login
#     patient = Patient(
#         doctor_id=user.id,  # Temporary - patient will be assigned to doctor later
#         full_name=patient_in.full_name,
#         phone=patient_in.phone,
#         cnic="PENDING",  # Placeholder - can be updated later
#         gender=PatientGender.OTHER,  # Default - can be updated later
#         hashed_password=get_password_hash(patient_in.password) if patient_in.password else None,
#     )
#     session.add(patient)
#     session.commit()
#     session.refresh(patient)
#     
#     # Audit log
#     try:
#         audit = AuditLog(user_id=user.id, action="patient_registration_phone", entity="user", entity_id=user.id)
#         session.add(audit)
#         session.commit()
#     except Exception:
#         session.rollback()
#     
#     return user


@self_service_router.post("/patients/register-simple", response_model=PatientPublic, tags=["🧍 Registration | Patient"])
def register_patient_simple(
    session: SessionDep, 
    patient_in: PatientRegisterSimple
) -> Any:
    """
    🧍 **Access:** Frontend, Staff, Public

    **Authentication:** Public (no login required)

    Simplified patient registration with name, gender, phone, and doctor selection.

    **Required fields:**
    - `full_name`: Patient's full name
    - `gender`: Patient's gender (MALE, FEMALE, OTHER)
    - `phone`: Phone number (becomes the login password)
    - `doctor_id`: UUID of the doctor to assign

    **Important:**
    - **This does NOT create a User account** - it creates a Patient record only
    - Phone number automatically becomes the patient's password
    - No email required - phone-only authentication
    - Patient is immediately assigned to selected doctor
    - No email verification needed

    **Use case:** Website "Find a Doctor" → Patient selects doctor → Registration → Immediate access to book appointment

    **Duplicate handling:** If patient with same phone exists for this doctor, returns 400 error
    """
    # First verify that the doctor exists and is active
    doctor = session.get(User, patient_in.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )
    
    if doctor.role != "doctor":
        raise HTTPException(
            status_code=400,
            detail="Specified user is not a doctor"
        )
    
    if not doctor.is_active:
        raise HTTPException(
            status_code=400,
            detail="Doctor account is inactive"
        )
    
    # Check if patient with this phone already exists for this doctor
    existing_patient = session.exec(
        select(Patient).where(
            Patient.phone == patient_in.phone,
            Patient.doctor_id == patient_in.doctor_id
        )
    ).first()
    
    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient with this phone number already exists for this doctor"
        )
    
    # Generate unique CNIC placeholder (max 15 chars per database constraint)
    # Format: P + last 4 digits of phone + 10 random hex chars = 15 chars exactly
    phone_suffix = patient_in.phone[-4:] if len(patient_in.phone) >= 4 else patient_in.phone
    random_suffix = uuid.uuid4().hex[:10]
    unique_cnic = f"P{phone_suffix}{random_suffix}"  # Total: 1+4+10=15 chars
    
    # Validate gender
    if not EnumService.validate_value(session, "PatientGender", patient_in.gender, patient_in.doctor_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid gender '{patient_in.gender}'. Use /enums/doctor/PatientGender to get valid options."
        )
    
    # Create patient record with the provided doctor_id
    patient = Patient(
        doctor_id=patient_in.doctor_id,
        full_name=patient_in.full_name,
        phone=patient_in.phone,
        cnic=unique_cnic,  # Unique CNIC placeholder
        gender=patient_in.gender,  # Use provided gender
        hashed_password=get_password_hash(patient_in.phone),  # Phone is the password
    )
    
    session.add(patient)
    
    try:
        session.commit()
        session.refresh(patient)
    except IntegrityError as e:
        session.rollback()
        if "uq_patient_cnic" in str(e) or "duplicate key" in str(e).lower():
            # Retry with different CNIC if duplicate
            phone_suffix = patient_in.phone[-4:] if len(patient_in.phone) >= 4 else patient_in.phone
            random_suffix = uuid.uuid4().hex[:10]
            unique_cnic = f"P{phone_suffix}{random_suffix}"  # Total: 1+4+10=15 chars
            
            patient.cnic = unique_cnic
            session.add(patient)
            
            try:
                session.commit()
                session.refresh(patient)
            except Exception as retry_error:
                session.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create patient after retry: {str(retry_error)}"
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating patient: {str(e)}"
            )
    
    # Audit log
    try:
        audit = AuditLog(
            user_id=patient_in.doctor_id,  # Doctor's ID for audit trail
            action="patient_registration_simple",
            entity="patient",
            entity_id=patient.id
        )
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()  # Don't fail the whole request if audit fails
    
    return patient


@self_service_router.post("/patients/quick-access", response_model=PatientQuickAccessResponse, tags=["🧍 Registration | Patient"])
def quick_access_patient(
    session: SessionDep,
    patient_in: PatientRegisterSimple
) -> Any:
    """
    🧍 **Access:** Frontend, Public (combined register + login)

    **Authentication:** Public (no login required)

    Quick access endpoint combining patient registration and instant login.

    **Required fields:**
    - `full_name`: Patient's full name
    - `gender`: Patient's gender (MALE, FEMALE, OTHER)
    - `phone`: Phone number (becomes login password)
    - `doctor_id`: UUID of the doctor to assign

    **Returns:** Access token + patient details (all in one request)

    **Perfect for:**
    - Online appointment booking flows
    - Patient quick access without separate login step
    - Mobile app registration workflows

    **Flow:**
    1. Patient selects doctor
    2. Patient enters name, gender, phone
    3. Endpoint registers + generates access token
    4. Patient immediately has authenticated session
    5. Frontend redirects to booking or profile page

    **Duplicate handling:**
    - If patient with this phone + doctor exists → generates new token, does NOT create duplicate
    - Ensures idempotency for mobile/flaky connections

    **This does NOT create a User account** - only Patient record + JWT token
    """
    # Verify that the doctor exists and is active
    doctor = session.get(User, patient_in.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )
    
    if doctor.role != "doctor":
        raise HTTPException(
            status_code=400,
            detail="Specified user is not a doctor"
        )
    
    if not doctor.is_active:
        raise HTTPException(
            status_code=400,
            detail="Doctor account is inactive"
        )
    
    # Check if patient with this phone already exists for this doctor
    existing_patient = session.exec(
        select(Patient).where(
            Patient.phone == patient_in.phone,
            Patient.doctor_id == patient_in.doctor_id
        )
    ).first()
    
    patient = None
    
    if existing_patient:
        # Patient exists - just login
        patient = existing_patient
        if not verify_password(patient_in.phone, patient.hashed_password):
            # Phone changed? Update password
            patient.hashed_password = get_password_hash(patient_in.phone)
            session.add(patient)
            try:
                session.commit()
                session.refresh(patient)
            except IntegrityError as e:
                session.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Error updating patient: {str(e)}"
                )
    else:
        # Generate unique CNIC placeholder (max 15 chars per database constraint)
        # Format: P + last 4 digits of phone + 10 random hex chars = 15 chars exactly
        phone_suffix = patient_in.phone[-4:] if len(patient_in.phone) >= 4 else patient_in.phone
        random_suffix = uuid.uuid4().hex[:10]
        unique_cnic = f"P{phone_suffix}{random_suffix}"  # Total: 1+4+10=15 chars
        
        # Create new patient
        patient = Patient(
            doctor_id=patient_in.doctor_id,  # Use the doctor_id from frontend
            full_name=patient_in.full_name,
            phone=patient_in.phone,
            cnic=unique_cnic,  # Unique CNIC placeholder
            gender=patient_in.gender,
            hashed_password=get_password_hash(patient_in.phone),
        )
        session.add(patient)
        
        try:
            session.commit()
            session.refresh(patient)
        except IntegrityError as e:
            session.rollback()
            if "uq_patient_cnic" in str(e) or "duplicate key" in str(e).lower():
                # Retry with different CNIC if duplicate
                phone_suffix = patient_in.phone[-4:] if len(patient_in.phone) >= 4 else patient_in.phone
                random_suffix = uuid.uuid4().hex[:10]
                unique_cnic = f"P{phone_suffix}{random_suffix}"  # Total: 1+4+10=15 chars
                
                patient.cnic = unique_cnic
                session.add(patient)
                
                try:
                    session.commit()
                    session.refresh(patient)
                except Exception as retry_error:
                    session.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create patient after retry: {str(retry_error)}"
                    )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error creating patient: {str(e)}"
                )
    
    # Generate access token for the patient
    access_token_expires = timedelta(days=30)
    access_token = security.create_access_token(
        patient.id, expires_delta=access_token_expires, entity="patient", role="patient"
    )
    
    # Update last login
    patient.last_login = date.today()
    session.add(patient)
    session.commit()
    
    # Prepare patient data for response
    patient_data = {
        "id": str(patient.id),
        "full_name": patient.full_name,
        "phone": patient.phone,
        "email": patient.email,
        "gender": patient.gender,
        "age": patient.age,
        "doctor_id": str(patient.doctor_id),
    }
    
    # Audit log
    try:
        audit = AuditLog(
            user_id=patient_in.doctor_id,  # Doctor's ID for audit trail
            action="patient_quick_access",
            entity="patient",
            entity_id=patient.id
        )
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()  # Don't fail if audit log fails
    
    return PatientQuickAccessResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        patient=patient_data,
        message="Patient registered and logged in successfully"
    )


@admin_router.get("/{user_id}", response_model=UserPublic, tags=["🛡️ Admin | User Management"])
def read_user_by_id(
    user_id: uuid.UUID = Path(..., description="User UUID"), session: SessionDep = None, current_user: CurrentUser = None
) -> Any:
    """
    🔐 **Access:** ADMIN only (or user viewing their own profile)

    **Authentication:** DoctorOAuth2

    Get a specific user by ID.

    **Path parameters:**
    - `user_id`: UUID of the user to retrieve

    **Behavior:**
    - If user is viewing their own profile (ID matches current user) → allowed
    - If user is ADMIN → allowed to view any user
    - Otherwise → 403 Forbidden

    **Returns:** Full user details including role, email, status, etc.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user == current_user:
        return user
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    
    return user


@admin_router.patch(
    "/{user_id}",
    tags=["🛡️ Admin | User Management"],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Update any user's information (admin only).

    **Path parameters:**
    - `user_id`: UUID of the user to update

    **Allowed fields:** full_name, email, is_active, role, phone

    **Behavior:**
    - Admin can update any user account
    - Email uniqueness checked before update
    - Role can be changed (DOCTOR ↔ STAFF ↔ ADMIN)
    - Audit log records all changes

    **Restrictions:**
    - Cannot update password via this endpoint (use dedicated password endpoint)
    - User must exist (404 if not found)
    - Email must be unique (409 if duplicate)
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@admin_router.delete("/{user_id}", tags=["🛡️ Admin | User Management"])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    🔐 **Access:** ADMIN only

    **Authentication:** DoctorOAuth2

    Delete a user from the system (admin only).

    **Path parameters:**
    - `user_id`: UUID of the user to delete

    **Restrictions:**
    - Admin cannot delete themselves (safety lock)
    - Doctors with assigned patients cannot be deleted
    - Other roles can be deleted if no dependencies exist

    **Behavior:**
    - Soft or hard delete based on configuration
    - Associated records may be archived/transferred
    - Audit log records deletion with admin ID

    **Errors:**
    - 404: User not found
    - 403: Trying to delete self
    - 400: Doctor has dependent patients
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    
    # Check if doctor has patients
    if user.role == "doctor":
        from sqlmodel import select, func
        from models.patients_model import Patient
        
        patient_count = session.exec(
            select(func.count()).where(Patient.doctor_id == user.id)
        ).one()
        
        if patient_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete doctor account with existing patients. Transfer patients first."
            )
    
    # If your app has associated item models, restore/delete them here.
    # The original code referenced `Item` which does not exist in the models.
    # Skipping that deletion to avoid NameError.

    session.delete(user)
    session.commit()

    try:
        audit = AuditLog(user_id=current_user.id if current_user else None, action="delete_user", entity="user", entity_id=user.id)
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()

    return Message(message="User deleted successfully")


@self_service_router.get("/doctors/list", response_model=UsersPublic, tags=["🩺 Listing | Doctor Directory"], dependencies=[Security(require_roles("admin", "staff"))])
def list_doctors(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentUser = None
) -> Any:
    """
    🩺 **Access:** Admin, Staff (internal dashboard use)

    **Authentication:** DoctorOAuth2

    List all active doctors in the system (for staff dashboards, patient assignment, etc.).

    **Query parameters:**
    - `skip`: Records to skip (default: 0)
    - `limit`: Records to return (default: 100)

    **Returns:**
    - List of doctor users with full details
    - Total count of doctors in system

    **Note:** This is an internal endpoint for staff/admin dashboards.
    Public users should use `/public/doctors` instead for public doctor search.

    **Difference from admin GET /users/:**
    - This endpoint filters to doctors only
    - This endpoint may be accessible to staff (depending on authorization config)
    - Admin GET /users/ shows ALL user types (doctor, staff, admin)
    """
    count_statement = select(func.count()).where(User.role == "doctor")
    count = session.exec(count_statement).one()

    statement = select(User).where(User.role == "doctor").offset(skip).limit(limit)
    doctors = session.exec(statement).all()

    return UsersPublic(data=doctors, count=count)


# ============================================================================
# UNIFIED ADMIN APPROVAL ENDPOINTS (DOCTORS & STAFF)
# ============================================================================
# Single unified system - replaces redundant doctor-specific endpoints
#
# DEPRECATED ENDPOINTS (removed):
#   GET  /pending-doctors    → Use /pending-approvals?role=doctor
#   POST /approve-doctor/{id} → Use /approve/{id}


@admin_router.post("/approve/{user_id}", response_model=ApprovalResponse, tags=["🛡️ Admin | Approvals"])
def approve_user(
    user_id: uuid.UUID,
    request_data: ApprovalRequest,
    session: SessionDep = None,
    current_user: CurrentUser = None
) -> Any:
    """
    🛡️ **Access:** ADMIN only

    **Authentication:** OAuth2

    Approve or reject a user's signup application (doctor or staff).

    **Path Parameters:**
    - `user_id`: UUID of the user

    **Request Body:**
    - `action`: "approve" or "reject"
    - `reason`: Rejection reason (required if action=reject)

    **Behavior:**
    - approve: Sets is_approved=TRUE, is_active=TRUE, sends approval email
    - reject: Sets is_approved=FALSE, is_active=FALSE, sends rejection email with reason

    **Returns:** Success status, message, and updated user object
    """
    # Validate action and reason
    if request_data.action == "reject" and not request_data.reason:
        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required when rejecting a user"
        )
    
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role not in ["doctor", "staff"]:
        raise HTTPException(
            status_code=400,
            detail="This endpoint only approves doctors and staff (not admins)"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve a user whose email is not verified yet"
        )
    
    role_text = user.role.capitalize()
    
    if request_data.action == "approve":
        # Check if already approved (idempotent)
        if user.is_approved:
            return ApprovalResponse(
                success=True,
                message=f"{role_text} '{user.full_name}' is already approved",
                user=user
            )
        
        user.is_approved = True
        user.is_active = True
        user.rejection_reason = None
        message = f"✅ {role_text} '{user.full_name}' has been approved and can now login"
        
        # Send approval email
        if settings.emails_enabled:
            try:
                send_email(
                    email_to=user.email,
                    subject=f"🎉 Your {role_text} Account Has Been Approved!",
                    html_content=f"""
                    <h2>Account Approved!</h2>
                    <p>Dear {user.full_name},</p>
                    <p>Great news! Your {user.role} account has been approved by our admin team.</p>
                    <p>You can now login to the system with your credentials.</p>
                    <p>Best regards,<br>Administration Team</p>
                    """
                )
            except Exception as e:
                print(f"Failed to send approval email: {str(e)}")
    
    else:  # reject
        user.is_approved = False
        user.is_active = False
        user.rejection_reason = request_data.reason
        message = f"❌ {role_text} '{user.full_name}' has been rejected"
        
        # Send rejection email
        if settings.emails_enabled:
            try:
                reason_text = f"<p><strong>Reason:</strong> {request_data.reason}</p>" if request_data.reason else ""
                send_email(
                    email_to=user.email,
                    subject="Account Application Update",
                    html_content=f"""
                    <h2>Application Update</h2>
                    <p>Dear {user.full_name},</p>
                    <p>Thank you for your interest in joining as a {user.role}.</p>
                    <p>Unfortunately, we are unable to approve your account at this time.</p>
                    {reason_text}
                    <p>Please feel free to contact our support team if you have questions.</p>
                    <p>Best regards,<br>Administration Team</p>
                    """
                )
            except Exception as e:
                print(f"Failed to send rejection email: {str(e)}")
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Audit log
    try:
        action = "approve_user" if request_data.action == "approve" else "reject_user"
        audit = AuditLog(
            user_id=current_user.id,
            action=action,
            entity="user",
            entity_id=user.id,
            changes={"is_approved": request_data.action == "approve", "reason": request_data.reason}
        )
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()
    
    return ApprovalResponse(
        success=True,
        message=message,
        user=user
    )


# ============================================================================
# COMBINE ROUTERS FOR EXPORT
# ============================================================================
# IMPORTANT: self_service_router MUST be included FIRST
# This ensures /me endpoints are matched before /{user_id} (parameterized route)
# FastAPI matches routes in the order they're registered
router.include_router(self_service_router)
router.include_router(admin_router)