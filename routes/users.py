import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlmodel import col, delete, func, select
import jwt

from utils import crud
from api.deps import (
    CurrentUser,
    SessionDep,
    TokenDep,
    get_current_active_superuser,
)
from core import security
from core.config import settings
from core.security import get_password_hash, verify_password
from models.login_model import Message
from models.patients_model import Patient, PatientPublic, PatientGender
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
    UserRole,
)
from models.public_models import PatientRegisterPublic, PatientRegisterPhoneOnly, PatientRegisterSimple, PatientQuickAccessResponse
from utils.utils import (
    generate_new_account_email,
    generate_email_verification_email,
    generate_email_verification_token,
    send_email
)
from models.audit_model import AuditLog

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)) -> Any:
    """
    Retrieve users.
    """
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()

    return UsersPublic(data=users, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user (admin only).
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    
    # Send verification email
    if settings.emails_enabled and user_in.email:
        verification_token = generate_email_verification_token(email=user_in.email)
        email_data = generate_email_verification_email(
            email_to=user_in.email, email=user_in.email, token=verification_token
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    
    # Audit log
    try:
        audit = AuditLog(user_id=user.id, action="create_user", entity="user", entity_id=user.id)
        session.add(audit)
        session.commit()
    except Exception:
        # Don't break user creation on audit failures
        session.rollback()
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
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


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
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


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
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


@router.get("/me/stats", response_model=DoctorStats)
def get_doctor_stats(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get doctor statistics.
    """
    from sqlmodel import func, select
    from models.patients_model import Patient
    from models.cases_model import PatientCase
    from models.appointments_model import Appointment
    from models.prescriptions_model import Prescription
    from models.medicines_model import DoctorMedicineStock
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
    
    # Get low stock items
    low_stock_items = session.exec(
        select(func.count()).where(
            DoctorMedicineStock.doctor_id == current_user.id,
            DoctorMedicineStock.quantity <= DoctorMedicineStock.low_stock_threshold,
            DoctorMedicineStock.is_active == True
        )
    ).one()
    
    return DoctorStats(
        total_patients=total_patients,
        total_cases=total_cases,
        total_appointments=total_appointments,
        total_prescriptions=total_prescriptions,
        upcoming_appointments=upcoming_appointments,
        pending_followups=0,  # You can add this calculation if needed
        low_stock_items=low_stock_items,
        revenue_today=0.0,  # You can add revenue calculations if needed
        revenue_this_month=0.0
    )


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
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


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
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
        role="doctor"  # Default role for signups is doctor
    )
    
    user = crud.create_user(session=session, user_create=user_create)
    
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
#     auto_email = f"patient_{patient_in.phone}@system.local"
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


@router.post("/patients/register-simple", response_model=UserPublic, tags=["patient-registration"])
def register_patient_simple(session: SessionDep, patient_in: PatientRegisterSimple) -> Any:
    """
    Simplified patient registration - name, gender, and phone only
    
    **Required fields:** full_name, gender, phone
    **No password required** - Phone number becomes the password for login
    **No email verification required**
    **Patient can login immediately with name + phone via /login/patient-simple**
    
    Creates a patient user account with minimal information.
    """
    # Check if patient with this phone already exists
    existing_patient = session.exec(
        select(Patient).where(Patient.phone == patient_in.phone)
    ).first()
    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient with this phone number already exists"
        )
    
    # Auto-generate email (since User model requires it)
    auto_email = f"patient_{patient_in.phone}@system.local"
    
    # Check if auto-generated email is already used
    user = crud.get_user_by_email(session=session, email=auto_email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="Patient registration failed. Please try again."
        )
    
    # Create user with PATIENT role (no email verification needed)
    # Use phone as temporary password
    user_create = UserCreate(
        email=auto_email,
        password=patient_in.phone,  # Phone is used as password
        full_name=patient_in.full_name,
        role=UserRole.PATIENT,
        phone=patient_in.phone,
        is_verified=True  # Skip email verification for phone-based registration
    )
    
    user = crud.create_user(session=session, user_create=user_create)
    
    # Create patient record in Patient table with phone as password
    patient = Patient(
        doctor_id=user.id,  # Temporary - patient will be assigned to doctor later
        full_name=patient_in.full_name,
        phone=patient_in.phone,
        cnic="PENDING",  # Placeholder - can be updated later
        gender=PatientGender(patient_in.gender),  # Use provided gender
        hashed_password=get_password_hash(patient_in.phone),  # Phone is the password
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Audit log
    try:
        audit = AuditLog(user_id=user.id, action="patient_registration_simple", entity="user", entity_id=user.id)
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()
    
    return user


@router.post("/patients/quick-access", response_model=PatientQuickAccessResponse, tags=["patient-registration"])
def quick_access_patient(session: SessionDep, patient_in: PatientRegisterSimple) -> Any:
    """
    Quick access endpoint for online appointment booking
    
    Combines patient registration and login in a single API call.
    Perfect for appointment booking flow where patient needs immediate access.
    
    **Required fields:** full_name, gender, phone
    **Returns:** Access token + Patient details
    **Use case:** Patient books appointment → Registers with details → Gets token → Can immediately access profile
    
    **Flow:**
    1. Patient fills name, gender, phone (+ problem description for appointment)
    2. This endpoint registers patient and returns access token
    3. Patient can immediately use token to book appointment or view profile
    
    **Benefits:** Only 2 API calls instead of 4 (register + login + book appointment)
    """
    # Check if patient with this phone already exists
    existing_patient = session.exec(
        select(Patient).where(Patient.phone == patient_in.phone)
    ).first()
    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient with this phone number already exists. Please login instead."
        )
    
    # Auto-generate email (since User model requires it)
    auto_email = f"patient_{patient_in.phone}@system.local"
    
    # Check if auto-generated email is already used
    user = crud.get_user_by_email(session=session, email=auto_email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="Patient registration failed. Please try again."
        )
    
    # Create user with PATIENT role
    user_create = UserCreate(
        email=auto_email,
        password=patient_in.phone,  # Phone is used as password
        full_name=patient_in.full_name,
        role=UserRole.PATIENT,
        phone=patient_in.phone,
        is_verified=True  # Skip email verification
    )
    
    user = crud.create_user(session=session, user_create=user_create)
    
    # Create patient record with phone as password
    patient = Patient(
        doctor_id=user.id,  # Temporary - will be assigned during appointment
        full_name=patient_in.full_name,
        phone=patient_in.phone,
        cnic="PENDING",
        gender=PatientGender(patient_in.gender),
        hashed_password=get_password_hash(patient_in.phone),
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Generate access token (like login endpoint)
    from datetime import timedelta
    access_token_expires = timedelta(days=30)
    access_token = security.create_access_token(
        patient.id, expires_delta=access_token_expires
    )
    
    # Update last login
    patient.last_login = datetime.now().date()
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
        audit = AuditLog(user_id=user.id, action="patient_quick_access", entity="user", entity_id=user.id)
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()
    
    return PatientQuickAccessResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        patient=patient_data,
        message="Patient registered and logged in successfully"
    )


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID = Path(..., description="User UUID"), session: SessionDep = None, current_user: CurrentUser = None
) -> Any:
    """
    Get a specific user by id.
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


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
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


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
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


@router.get("/doctors/list", response_model=UsersPublic)
def list_doctors(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentUser = None
) -> Any:
    """
    List all doctors.
    """
    count_statement = select(func.count()).where(User.role == "doctor")
    count = session.exec(count_statement).one()

    statement = select(User).where(User.role == "doctor").offset(skip).limit(limit)
    doctors = session.exec(statement).all()

    return UsersPublic(data=doctors, count=count)