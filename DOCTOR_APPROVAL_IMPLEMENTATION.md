# Doctor Approval System - Implementation Complete

## Overview
Added a simplified doctor approval workflow with minimal changes to the existing system.

---

## Changes Made

### 1. Database Model Changes
**File:** `models/users_model.py`

**Added field to UserBase:**
```python
is_approved: bool = Field(default=False)  # Admin approval for doctors
```

**Database migration needed:**
```sql
ALTER TABLE "user" 
ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT FALSE;

-- Create index for faster queries
CREATE INDEX idx_user_is_approved ON "user"(is_approved);
```

---

### 2. API Schema Updates
**File:** `models/users_model.py`

**Updated UserRegister to include doctor verification fields:**
```python
class UserRegister(SQLModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str]
    # NEW doctor fields:
    registration_number: Optional[str]  # Medical license
    specialization: Optional[str]       # Medical specialty
    clinic_name: Optional[str]          # Practice name
    clinic_address: Optional[str]       # Practice address
```

---

### 3. Signup Endpoint Changes
**File:** `routes/users.py` - POST `/users/signup`

**New behavior:**
- Collects doctor verification details upfront
- Sets initial status:
  - `is_verified = FALSE` (pending email confirmation)
  - `is_approved = FALSE` (pending admin approval)
  - `is_active = FALSE` (can't login)
- Sends email verification link

---

### 4. Login Endpoint Changes
**File:** `routes/login.py` - Both `/login/access-token` and `/login`

**Added approval check:**
```python
elif user.role == "doctor" and not user.is_approved:
    raise HTTPException(
        status_code=403,
        detail="Your account is pending admin approval. You'll receive an email when approved."
    )
```

**Login now requires for doctors:**
1. ✅ Valid credentials
2. ✅ Email verified (is_verified=TRUE)
3. ✅ Account approved (is_approved=TRUE) ← NEW
4. ✅ Account active (is_active=TRUE)

---

### 5. New Admin Approval Endpoints
**File:** `routes/users.py`

#### GET `/users/pending-doctors`
- Lists all doctors waiting for approval
- Admin-only endpoint
- Returns count + list of pending doctors
- Filters: role="doctor", is_verified=TRUE, is_approved=FALSE

#### POST `/users/approve-doctor/{doctor_id}?approve=true/false`
- Approve or reject a doctor account
- Admin-only endpoint
- Parameters:
  - `approve=true` → Approves and activates account, sends approval email
  - `approve=false` → Rejects account, sends rejection email
- Logs action in audit trail
- Returns updated user object

---

## Complete Doctor Signup Flow

```
1. SIGNUP (Doctor submits form)
   ├─ Email: doctor@example.com
   ├─ Full Name: Dr. Ahmed Khan
   ├─ Registration #: PMC-12345
   ├─ Specialization: Cardiologist
   ├─ Clinic: City Hospital
   └─ Status: is_verified=F, is_approved=F, is_active=F

   ↓ (Verification email sent)

2. EMAIL VERIFICATION (Doctor clicks link)
   └─ Status: is_verified=T, is_approved=F, is_active=F
      ⚠️ Can't login yet (needs approval)

   ↓ (Admin gets notification)

3. ADMIN REVIEW (Admin checks pending doctors)
   ├─ Admin visits: GET /users/pending-doctors
   ├─ Sees: Dr. Ahmed Khan's details
   ├─ Verifies: Registration #, License, Clinic
   └─ Clicks: "Approve" button

   ↓ (Approval request sent)

4. ACCOUNT APPROVAL (Admin clicks approve)
   ├─ POST /users/approve-doctor/{doctor_id}?approve=true
   └─ Status: is_verified=T, is_approved=T, is_active=T

   ↓ (Approval email sent)

5. DOCTOR LOGIN (Doctor can now login)
   ├─ POST /login
   ├─ Email: doctor@example.com
   ├─ Password: ********
   ├─ All checks pass ✓
   └─ Login successful → Dashboard
```

---

## Account Status Legend

| State | is_verified | is_approved | is_active | Can Login? |
|-------|---|---|---|---|
| Just signed up | ❌ | ❌ | ❌ | ❌ NO |
| Email verified | ✅ | ❌ | ❌ | ❌ NO |
| Admin approved | ✅ | ✅ | ✅ | ✅ YES |
| Admin rejected | ✅ | ❌ | ❌ | ❌ NO |
| Suspended | ✅ | ✅ | ❌ | ❌ NO |

---

## SQL Migration Script

```sql
-- Add is_approved column
ALTER TABLE "user" 
ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT FALSE;

-- Create index for approval queries
CREATE INDEX idx_user_is_approved ON "user"(is_approved);
CREATE INDEX idx_user_role_verified_approved ON "user"(role, is_verified, is_approved);

-- Set existing doctors/staff as approved (they were already verified)
UPDATE "user" 
SET is_approved = TRUE 
WHERE role IN ('doctor', 'staff') 
AND is_verified = TRUE;
```

---

## Files Modified

1. **models/users_model.py**
   - Added `is_approved: bool` field to UserBase
   - Updated UserRegister schema with doctor verification fields

2. **routes/login.py**
   - Added approval check to `/login/access-token` endpoint
   - Added approval check to `/login` endpoint

3. **routes/users.py**
   - Updated `/users/signup` to collect doctor info
   - Set `is_approved=False` and `is_active=False` on new signups
   - Added `/users/pending-doctors` (list pending approvals)
   - Added `/users/approve-doctor/{doctor_id}` (approve/reject)
   - Added Swagger tags for admin approval endpoints

---

## Testing Checklist

- [ ] Database migration applied successfully
- [ ] Doctor can signup with all fields
- [ ] Doctor receives email verification link
- [ ] Doctor can't login before approving email
- [ ] Admin can list pending doctors
- [ ] Admin can approve doctor
- [ ] Doctor receives approval email
- [ ] Doctor can login after approval
- [ ] Admin can reject doctor
- [ ] Doctor receives rejection email
- [ ] Rejected doctor can't login
- [ ] Existing doctors still work (backward compatible)

---

## Security Notes

✅ Passwords are hashed (existing)  
✅ Email verification required (existing)  
✅ Admin approval required (NEW) ← NEW  
✅ Account active check required (existing)  
✅ Audit logging (existing, extended)  
✅ Rate limiting on login (existing)  
✅ Role-based access control (existing)  

---

## Backend Compatibility

- ✅ No breaking changes to existing endpoints
- ✅ New fields are optional in UserRegister
- ✅ Backward compatible with existing database
- ✅ Existing doctors/staff not affected
- ✅ Only new doctor signups require approval

---

## Frontend Changes Needed

1. **Signup Form:**
   - Add fields: registration_number, specialization, clinic_name, clinic_address
   - Add explanatory text about approval process

2. **Login Error Handling:**
   - Handle 403 with message: "Account pending admin approval"
   - Show helpful message to user

3. **Admin Dashboard:**
   - Add "Pending Doctors" section
   - List doctors with approve/reject buttons
   - Show: name, email, specialization, registration#, clinic

---

**Status:** ✅ Implementation Complete  
**Date:** February 6, 2026  
**Backward Compatible:** Yes  
**Migration Required:** Yes (SQL script above)
