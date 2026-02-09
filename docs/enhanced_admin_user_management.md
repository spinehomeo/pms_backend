# Updated Admin User Management Endpoints

## 🔄 Enhanced Endpoints with Approval System Integration

---

## 📋 Endpoint Overview

```
GET    /admin/users                  → List all users with filters
POST   /admin/users                  → Create user (auto-approved)
GET    /admin/users/{user_id}        → Get user by ID
PATCH  /admin/users/{user_id}        → Update user
DELETE /admin/users/{user_id}        → Delete user
GET    /admin/users/stats            → User statistics
```

---

## 1️⃣ GET /admin/users - List All Users (Enhanced)

### Description
Get all users in the system with enhanced filtering options including approval status.

### Endpoint
```
GET /admin/users
```

### Query Parameters
```python
role: str | None = None              # Filter: "doctor", "staff", "admin"
is_approved: bool | None = None      # Filter: true, false, or null for all
is_verified: bool | None = None      # Filter: true, false, or null for all
is_active: bool | None = None        # Filter: true, false, or null for all
search: str | None = None            # Search by name or email
skip: int = 0                        # Pagination offset
limit: int = 100                     # Results per page (max 1000)
```

### Implementation

```python
from typing import Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

router = APIRouter(prefix="/admin", tags=["🛡️ Admin | User Management"])


@router.get("/users", response_model=UsersPublic)
async def read_users(
    role: Literal["doctor", "staff", "admin"] | None = None,
    is_approved: bool | None = None,
    is_verified: bool | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    🛡️ **Access:** ADMIN only
    
    **Authentication:** DoctorOAuth2
    
    Retrieve all users with advanced filtering.
    
    **Query Parameters:**
    - `role`: Filter by role (doctor, staff, admin)
    - `is_approved`: Filter by approval status
    - `is_verified`: Filter by email verification status
    - `is_active`: Filter by active status
    - `search`: Search by name or email (case-insensitive)
    - `skip`: Pagination offset (default: 0)
    - `limit`: Results per page (default: 100, max: 1000)
    
    **Examples:**
    - Get all pending doctors: `?role=doctor&is_approved=false&is_verified=true`
    - Get all active staff: `?role=staff&is_active=true`
    - Search users: `?search=ahmed`
    
    **Returns:** 
    - List of users
    - Total count
    """
    
    # Base query
    query = db.query(User)
    
    # Apply filters
    if role:
        query = query.filter(User.role == role)
    
    if is_approved is not None:
        query = query.filter(User.is_approved == is_approved)
    
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.phone.ilike(search_pattern)
            )
        )
    
    # Order by most recent first
    query = query.order_by(User.created_at.desc())
    
    # Get total count
    total_count = query.count()
    
    # Get paginated results
    users = query.offset(skip).limit(limit).all()
    
    return UsersPublic(
        data=users,
        count=total_count
    )
```

### Usage Examples

```bash
# Get all users
GET /admin/users

# Get all doctors
GET /admin/users?role=doctor

# Get pending approvals (verified but not approved)
GET /admin/users?is_verified=true&is_approved=false

# Get only active users
GET /admin/users?is_active=true

# Search for specific user
GET /admin/users?search=ahmed

# Complex filter: active doctors who are approved
GET /admin/users?role=doctor&is_active=true&is_approved=true

# Pagination
GET /admin/users?skip=0&limit=20
```

---

## 2️⃣ POST /admin/users - Create User (Enhanced)

### Description
Admin creates a new user directly. Unlike public signup, admin-created users are **auto-approved and auto-verified**.

### Endpoint
```
POST /admin/users
```

### Request Body Schema

```python
class UserCreate(BaseModel):
    """Enhanced user creation schema for admin"""
    
    # Required fields
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)
    role: Literal["doctor", "staff", "admin"]
    
    # Optional fields
    phone: str | None = Field(None, max_length=20)
    
    # Doctor-specific fields
    registration_number: str | None = Field(None, max_length=100)
    specialization: str | None = Field(None, max_length=255)
    clinic_name: str | None = Field(None, max_length=255)
    clinic_address: str | None = None
    consultation_fee: float | None = Field(None, ge=0)
    
    # Admin can override default approval settings
    is_verified: bool = True      # Default: auto-verified
    is_approved: bool = True      # Default: auto-approved
    is_active: bool = True        # Default: active
```

### Implementation

```python
@router.post("/users", response_model=UserPublic)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    🛡️ **Access:** ADMIN only
    
    **Authentication:** DoctorOAuth2
    
    Create a new user directly (bypasses approval process).
    
    **Key Differences from Public Signup:**
    - User is **auto-verified** (no email verification needed)
    - User is **auto-approved** (no admin approval needed)
    - User is **immediately active** (can login right away)
    - Admin can set all fields directly
    - No email verification sent
    
    **Use Cases:**
    - Admin creating staff accounts
    - Admin creating doctor accounts manually
    - Bulk user imports
    - Migration from old system
    
    **Required Fields:**
    - `email`: Unique email address
    - `password`: Secure password (min 8 chars)
    - `full_name`: User's full name
    - `role`: "doctor", "staff", or "admin"
    
    **Optional Fields (Doctor-specific):**
    - `registration_number`: Medical license
    - `specialization`: Medical specialty
    - `clinic_name`: Practice name
    - `clinic_address`: Practice address
    - `consultation_fee`: Fee amount
    
    **Behavior:**
    - Checks email uniqueness
    - Hashes password securely
    - Sets is_verified = TRUE
    - Sets is_approved = TRUE
    - Sets is_active = TRUE
    - Sends welcome email (optional)
    - Logs creation in audit trail
    """
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        phone=user_in.phone,
        
        # Doctor-specific fields
        registration_number=user_in.registration_number,
        specialization=user_in.specialization,
        clinic_name=user_in.clinic_name,
        clinic_address=user_in.clinic_address,
        consultation_fee=user_in.consultation_fee,
        
        # CRITICAL: Admin-created users are auto-approved
        is_verified=user_in.is_verified,    # Default: TRUE
        is_approved=user_in.is_approved,    # Default: TRUE
        is_active=user_in.is_active,        # Default: TRUE
        
        # Audit fields
        created_by=current_user.id,
        approved_by=current_user.id,
        approved_at=datetime.utcnow()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Optional: Send welcome email
    send_welcome_email(user, password=user_in.password)
    
    # Log audit trail
    create_audit_log(
        db=db,
        action="user_created_by_admin",
        user_id=user.id,
        performed_by=current_user.id,
        details={
            "user_name": user.full_name,
            "user_role": user.role,
            "user_email": user.email,
            "auto_approved": True
        }
    )
    
    return user
```

### Usage Example

```bash
POST /admin/users

Request Body:
{
  "email": "newstaff@clinic.com",
  "password": "SecurePass123!",
  "full_name": "Sarah Johnson",
  "role": "staff",
  "phone": "+92-300-9876543",
  "is_verified": true,
  "is_approved": true,
  "is_active": true
}

Response: 200 OK
{
  "id": "uuid-here",
  "email": "newstaff@clinic.com",
  "full_name": "Sarah Johnson",
  "role": "staff",
  "is_verified": true,
  "is_approved": true,
  "is_active": true,
  "join_date": "2026-02-06"
}
```

---

## 3️⃣ GET /admin/users/{user_id} - Get User By ID (Enhanced)

### Implementation

```python
@router.get("/users/{user_id}", response_model=UserPublic)
async def read_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    🛡️ **Access:** ADMIN only
    
    **Authentication:** DoctorOAuth2
    
    Get detailed information about a specific user.
    
    **Path Parameters:**
    - `user_id`: UUID of the user
    
    **Returns:**
    - Full user details including:
      - Basic info (name, email, role)
      - Status flags (verified, approved, active)
      - Doctor-specific fields (if doctor)
      - Timestamps (created, approved, last login)
      - Audit info (created by, approved by)
    
    **Note:** This is admin-only. Regular users use /users/me
    """
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return user
```

---

## 4️⃣ PATCH /admin/users/{user_id} - Update User (Enhanced)

### Request Body Schema

```python
class UserUpdate(BaseModel):
    """Enhanced user update schema"""
    
    # Basic fields
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    role: Literal["doctor", "staff", "admin"] | None = None
    
    # Doctor-specific fields
    specialization: str | None = Field(None, max_length=255)
    registration_number: str | None = Field(None, max_length=100)
    clinic_name: str | None = Field(None, max_length=255)
    clinic_address: str | None = None
    consultation_fee: float | None = Field(None, ge=0)
    
    # Status flags - ADMIN CAN CHANGE THESE
    is_verified: bool | None = None
    is_approved: bool | None = None
    is_active: bool | None = None
```

### Implementation

```python
@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    🛡️ **Access:** ADMIN only
    
    **Authentication:** DoctorOAuth2
    
    Update any user's information.
    
    **Path Parameters:**
    - `user_id`: UUID of user to update
    
    **Updateable Fields:**
    - Basic: email, full_name, phone, role
    - Doctor: specialization, registration_number, clinic_name, etc.
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
    user = db.query(User).filter(User.id == user_id).first()
    
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
        existing = db.query(User).filter(
            User.email == update_data["email"],
            User.id != user_id
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
            "from": user.role,
            "to": update_data["role"]
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
    
    # If approving user, set approval metadata
    if update_data.get("is_approved") == True and not user.approved_at:
        user.approved_by = current_user.id
        user.approved_at = datetime.utcnow()
    
    # If un-approving user, clear approval metadata
    if update_data.get("is_approved") == False:
        user.approved_by = None
        user.approved_at = None
    
    db.commit()
    db.refresh(user)
    
    # Log audit trail
    if changes:
        create_audit_log(
            db=db,
            action="user_updated_by_admin",
            user_id=user.id,
            performed_by=current_user.id,
            details={
                "user_name": user.full_name,
                "changes": changes
            }
        )
    
    return user
```

### Usage Examples

```bash
# Activate a deactivated user
PATCH /admin/users/{user_id}
{
  "is_active": true
}

# Manually approve a user
PATCH /admin/users/{user_id}
{
  "is_approved": true,
  "is_verified": true
}

# Change user role
PATCH /admin/users/{user_id}
{
  "role": "staff"
}

# Update doctor details
PATCH /admin/users/{user_id}
{
  "specialization": "Orthopedic Surgeon",
  "consultation_fee": 5000
}

# Suspend user (keep approved but deactivate)
PATCH /admin/users/{user_id}
{
  "is_active": false
}
```

---

## 5️⃣ DELETE /admin/users/{user_id} - Delete User (Enhanced)

### Implementation

```python
@router.delete("/users/{user_id}", response_model=Message)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    🛡️ **Access:** ADMIN only
    
    **Authentication:** DoctorOAuth2
    
    Delete a user from the system.
    
    **Path Parameters:**
    - `user_id`: UUID of user to delete
    
    **Restrictions:**
    - Cannot delete yourself (safety measure)
    - Cannot delete other super users/admins (optional safety)
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
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Safety: Cannot delete yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account. Use self-service endpoint instead."
        )
    
    # Safety: Cannot delete other admins (optional)
    if user.role == "admin" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete admin users"
        )
    
    # Optional: Check for dependencies (e.g., assigned patients)
    if user.role == "doctor":
        patient_count = db.query(Patient).filter(
            Patient.doctor_id == user.id
        ).count()
        
        if patient_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete doctor with {patient_count} assigned patients. Transfer patients first."
            )
    
    # Log before deletion
    create_audit_log(
        db=db,
        action="user_deleted_by_admin",
        user_id=user.id,
        performed_by=current_user.id,
        details={
            "user_name": user.full_name,
            "user_email": user.email,
            "user_role": user.role
        }
    )
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return Message(
        message=f"User '{user.full_name}' ({user.role}) has been deleted"
    )
```

---

## 6️⃣ GET /admin/users/stats - User Statistics (NEW)

### Implementation

```python
class UserStats(BaseModel):
    """User statistics for admin dashboard"""
    total_users: int
    active_users: int
    inactive_users: int
    
    total_doctors: int
    active_doctors: int
    pending_doctors: int
    
    total_staff: int
    active_staff: int
    pending_staff: int
    
    total_admins: int
    
    pending_verification: int  # Signed up but not verified email
    pending_approval: int      # Verified but not approved
    
    created_today: int
    created_this_week: int
    created_this_month: int


@router.get("/users/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    🛡️ **Access:** ADMIN only
    
    **Authentication:** DoctorOAuth2
    
    Get comprehensive user statistics for admin dashboard.
    
    **Returns:**
    - Total users by role
    - Active vs inactive counts
    - Pending approvals/verifications
    - Recent signup trends
    """
    
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Total users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users
    
    # Doctors
    total_doctors = db.query(User).filter(User.role == "doctor").count()
    active_doctors = db.query(User).filter(
        User.role == "doctor",
        User.is_active == True
    ).count()
    pending_doctors = db.query(User).filter(
        User.role == "doctor",
        User.is_verified == True,
        User.is_approved == False
    ).count()
    
    # Staff
    total_staff = db.query(User).filter(User.role == "staff").count()
    active_staff = db.query(User).filter(
        User.role == "staff",
        User.is_active == True
    ).count()
    pending_staff = db.query(User).filter(
        User.role == "staff",
        User.is_verified == True,
        User.is_approved == False
    ).count()
    
    # Admins
    total_admins = db.query(User).filter(User.role == "admin").count()
    
    # Pending counts
    pending_verification = db.query(User).filter(
        User.is_verified == False,
        User.role.in_(["doctor", "staff"])
    ).count()
    
    pending_approval = db.query(User).filter(
        User.is_verified == True,
        User.is_approved == False,
        User.role.in_(["doctor", "staff"])
    ).count()
    
    # Recent signups
    created_today = db.query(User).filter(
        User.created_at >= today
    ).count()
    
    created_this_week = db.query(User).filter(
        User.created_at >= week_ago
    ).count()
    
    created_this_month = db.query(User).filter(
        User.created_at >= month_ago
    ).count()
    
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
```

---

## 📊 Comparison: Old vs New

### Old Endpoints
```
GET    /users/                    → Basic list, no approval filters
POST   /users/                    → Creates user, unclear approval status
GET    /users/{user_id}          → Basic user info
PATCH  /users/{user_id}          → Basic update
DELETE /users/{user_id}          → Basic delete
```

### New Enhanced Endpoints
```
GET    /admin/users               → Advanced filters (role, approval, status, search)
POST   /admin/users               → Auto-approved, clear documentation
GET    /admin/users/{user_id}     → Full details including approval metadata
PATCH  /admin/users/{user_id}     → Can update approval flags
DELETE /admin/users/{user_id}     → Safe deletion with checks
GET    /admin/users/stats         → NEW: Dashboard statistics
```

---

## 🔑 Key Improvements

### 1. **Approval System Integration**
- All endpoints now aware of `is_approved` flag
- Can filter users by approval status
- Can manually approve/unapprove users

### 2. **Enhanced Filtering**
- Filter by role, status, approval
- Search by name/email
- Combine multiple filters

### 3. **Admin Powers**
- Auto-approve users created by admin
- Manually override approval status
- Bulk operations possible

### 4. **Better Documentation**
- Clear descriptions of what each field does
- Examples for common use cases
- Security notes and restrictions

### 5. **Audit Trail**
- Log all admin actions
- Track who approved/created users
- Maintain accountability

---

## 📝 Usage Scenarios

### Scenario 1: Admin Creates Staff Member
```bash
POST /admin/users
{
  "email": "receptionist@clinic.com",
  "password": "TempPass123!",
  "full_name": "Jane Doe",
  "role": "staff"
}

# Result: User created, auto-approved, can login immediately
```

### Scenario 2: Review Pending Doctors
```bash
GET /admin/users?role=doctor&is_approved=false&is_verified=true

# Returns: List of doctors who verified email but need approval
```

### Scenario 3: Manually Approve User
```bash
PATCH /admin/users/uuid-here
{
  "is_approved": true,
  "is_active": true
}

# Result: User can now login
```

### Scenario 4: Suspend User
```bash
PATCH /admin/users/uuid-here
{
  "is_active": false
}

# Result: User cannot login but data preserved
```

### Scenario 5: Get Dashboard Stats
```bash
GET /admin/users/stats

# Returns: Complete overview of all users
```

---

## ✅ Summary

### What Changed:
1. ✅ All endpoints moved to `/admin/users` namespace
2. ✅ Added approval status filtering
3. ✅ Admin-created users are auto-approved
4. ✅ Can manually change approval status
5. ✅ Added search functionality
6. ✅ Added statistics endpoint
7. ✅ Better documentation with examples
8. ✅ Audit logging for all actions

### Key Benefits:
- **Unified System**: All user management in one place
- **Flexible**: Filter by any status combination
- **Powerful**: Admin can override any setting
- **Transparent**: Clear what each action does
- **Auditable**: All changes are logged
- **Safe**: Protection against self-deletion

### Migration Path:
```
Old: POST /users/
New: POST /admin/users (with auto-approval)

Old: GET /users/?skip=0&limit=100
New: GET /admin/users?skip=0&limit=100&is_active=true

Old: PATCH /users/{id}
New: PATCH /admin/users/{id} (can now change approval status)
```
