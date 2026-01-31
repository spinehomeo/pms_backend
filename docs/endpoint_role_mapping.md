# API Endpoint Role Mapping Guide
## Spine Homeo API - Complete Role-Based Access Reference

---

## Quick Reference Summary

| Role | Total Endpoints | Access Level |
|------|----------------|--------------|
| **PUBLIC** | 15 | No authentication required |
| **PATIENT** | 8 | Patient authentication only |
| **DOCTOR** | 23 | Doctor-specific functions |
| **DOCTOR + STAFF** | 37 | Doctor and staff shared access |
| **ALL AUTHENTICATED USERS** | 16 | Doctor, staff, and admin |
| **ADMIN ONLY** | 11 | Administrator exclusive |

**Total Endpoints: 110**

---

## Table of Contents

1. [Public Endpoints (No Authentication)](#1-public-endpoints)
2. [Patient-Only Endpoints](#2-patient-only-endpoints)
3. [Doctor-Only Endpoints](#3-doctor-only-endpoints)
4. [Doctor & Staff Endpoints](#4-doctor--staff-endpoints)
5. [All Authenticated Users (Doctor/Staff/Admin)](#5-all-authenticated-users)
6. [Admin-Only Endpoints](#6-admin-only-endpoints)
7. [Quick Lookup Table](#7-quick-lookup-table)
8. [Permission Matrix](#8-permission-matrix)

---

## 1. Public Endpoints (No Authentication)

These endpoints are accessible without any authentication token.

### 🔑 Authentication (7 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/login/access-token` | OAuth2 doctor/staff/admin login |
| `POST` | `/login` | Simplified doctor/staff/admin login |
| `POST` | `/login/patient-simple` | Patient login with name + phone |
| `POST` | `/password-recovery` | Request password reset |
| `POST` | `/reset-password/` | Reset password with token |
| `POST` | `/verify-email/{token}` | Verify email address |
| `POST` | `/resend-verification` | Resend verification email |

### 🧑‍⚕️ User Registration (1 endpoint)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/signup/register` | Register new doctor/staff |

### 🌍 Public Information (6 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/clinic-settings/public` | Get public clinic information |
| `GET` | `/availability/week/{doctor_id}` | Get doctor's weekly availability |
| `GET` | `/appointments/available-slots/{doctor_id}` | Get available appointment slots |
| `POST` | `/appointments/book` | Book appointment (patient registration) |
| `POST` | `/patients/` | Create new patient (registration) |
| `GET` | `/medicines/search` | Search medicine database |

### 📊 Reports (1 endpoint)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/reports/public/daily-appointments` | Public daily appointments report |

**Use Cases:**
- Patient self-registration
- Appointment booking for walk-ins
- Public clinic information
- Password recovery
- Email verification

---

## 2. Patient-Only Endpoints

Requires **PatientBearer** authentication (JWT from `/login/patient-simple`).

### 🧍 Patient Profile & Management (4 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/patients/me` | Get own patient profile |
| `PATCH` | `/patients/me` | Update own patient profile |
| `PUT` | `/patients/me/password` | Change own password |
| `DELETE` | `/patients/me` | Delete own patient account |

### 📅 Patient Appointments (2 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/appointments/patient/my-appointments` | View own appointments |
| `DELETE` | `/appointments/patient/{id}` | Cancel own appointment |

### 📝 Patient Prescriptions (1 endpoint)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/prescriptions/patient/my-prescriptions` | View own prescriptions |

### 📋 Patient Cases (1 endpoint)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/cases/patient/my-cases` | View own medical cases |

**Use Cases:**
- Patient self-service portal
- View medical history
- Manage appointments
- Update personal information

---

## 3. Doctor-Only Endpoints

Requires **DoctorOAuth2** authentication with **DOCTOR** role specifically.

### ⏰ Doctor Availability Management (11 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/availability/` | List doctor's availability settings |
| `POST` | `/availability/` | Create availability schedule |
| `GET` | `/availability/{id}` | Get specific availability entry |
| `PUT` | `/availability/{id}` | Update availability entry |
| `DELETE` | `/availability/{id}` | Delete availability entry |
| `POST` | `/availability/bulk` | Bulk create availability |
| `DELETE` | `/availability/bulk-delete` | Bulk delete availability |
| `POST` | `/availability/block-slot` | Block specific time slot |
| `DELETE` | `/availability/unblock-slot/{id}` | Unblock time slot |
| `GET` | `/availability/blocked-slots` | List blocked time slots |
| `GET` | `/availability/my-schedule` | Get doctor's full schedule |

### ⚙️ Doctor Preferences (5 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/doctor-preferences/` | Get doctor's preferences |
| `PUT` | `/doctor-preferences/` | Update doctor's preferences |
| `GET` | `/doctor-preferences/templates` | Get prescription templates |
| `POST` | `/doctor-preferences/templates` | Create prescription template |
| `DELETE` | `/doctor-preferences/templates/{id}` | Delete prescription template |

### 📝 Prescription Management (5 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/prescriptions/doctor/` | List all prescriptions by doctor |
| `POST` | `/prescriptions/doctor/` | Create new prescription |
| `GET` | `/prescriptions/doctor/{id}` | Get prescription details |
| `PUT` | `/prescriptions/doctor/{id}` | Update prescription |
| `DELETE` | `/prescriptions/doctor/{id}` | Delete prescription |

### 📋 Case Management (2 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/cases/` | Create new medical case |
| `PUT` | `/cases/{id}/close` | Close medical case |

**Use Cases:**
- Doctor's daily schedule management
- Prescription creation and management
- Personal preference settings
- Template management for common prescriptions

---

## 4. Doctor & Staff Endpoints

Requires **DoctorOAuth2** authentication with **DOCTOR** or **STAFF** role.

### 📅 Appointment Management (8 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/appointments/` | List all appointments |
| `GET` | `/appointments/{id}` | Get appointment details |
| `PUT` | `/appointments/{id}` | Update appointment |
| `DELETE` | `/appointments/{id}` | Delete appointment |
| `PATCH` | `/appointments/{id}/status` | Update appointment status |
| `GET` | `/appointments/today` | Get today's appointments |
| `GET` | `/appointments/upcoming` | Get upcoming appointments |
| `GET` | `/appointments/search` | Search appointments |

### 🧍 Patient Management (10 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/patients/` | List all patients |
| `GET` | `/patients/{id}` | Get patient details |
| `PUT` | `/patients/{id}` | Update patient information |
| `DELETE` | `/patients/{id}` | Delete patient record |
| `GET` | `/patients/search` | Search patients |
| `GET` | `/patients/{id}/appointments` | Get patient's appointments |
| `GET` | `/patients/{id}/prescriptions` | Get patient's prescriptions |
| `GET` | `/patients/{id}/cases` | Get patient's medical cases |
| `GET` | `/patients/{id}/history` | Get patient's medical history |
| `POST` | `/patients/{id}/notes` | Add notes to patient record |

### 💊 Medicine Management (9 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/medicines/` | List all medicines |
| `POST` | `/medicines/` | Add new medicine |
| `GET` | `/medicines/{id}` | Get medicine details |
| `PUT` | `/medicines/{id}` | Update medicine information |
| `DELETE` | `/medicines/{id}` | Delete medicine |
| `POST` | `/medicines/bulk-import` | Import medicines in bulk |
| `GET` | `/medicines/categories` | Get medicine categories |
| `GET` | `/medicines/low-stock` | Get low stock medicines |
| `PATCH` | `/medicines/{id}/stock` | Update medicine stock |

### 🔔 Follow-up Management (8 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/follow-ups/` | List all follow-ups |
| `POST` | `/follow-ups/` | Create follow-up reminder |
| `GET` | `/follow-ups/{id}` | Get follow-up details |
| `PUT` | `/follow-ups/{id}` | Update follow-up |
| `DELETE` | `/follow-ups/{id}` | Delete follow-up |
| `GET` | `/follow-ups/due` | Get due follow-ups |
| `PATCH` | `/follow-ups/{id}/complete` | Mark follow-up as complete |
| `GET` | `/follow-ups/patient/{patient_id}` | Get patient's follow-ups |

### 📋 Case Viewing (2 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/cases/` | List all medical cases |
| `GET` | `/cases/{id}` | Get case details |

**Use Cases:**
- Front desk operations
- Patient check-in/check-out
- Appointment scheduling
- Inventory management
- Patient record access

---

## 5. All Authenticated Users (Doctor/Staff/Admin)

Requires **DoctorOAuth2** authentication. Accessible by all three roles.

### 👥 User Profile Management (4 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/users/me` | Get own user profile |
| `PATCH` | `/users/me` | Update own user profile |
| `PATCH` | `/users/me/password` | Change own password |
| `DELETE` | `/users/me` | Delete own user account |

### 🔑 Session Management (2 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/login/test-token` | Test access token validity |
| `GET` | `/session` | Get current session information |

### 📊 Reports - General (5 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/reports/appointments/summary` | Appointment summary report |
| `GET` | `/reports/patients/new` | New patients report |
| `GET` | `/reports/revenue/summary` | Revenue summary report |
| `GET` | `/reports/doctor/performance` | Doctor performance report |
| `GET` | `/reports/custom` | Custom report generation |

### 🛠️ Utilities (4 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/utils/healthcheck` | API health check |
| `GET` | `/utils/version` | API version information |
| `POST` | `/utils/send-notification` | Send notification |
| `GET` | `/utils/system-stats` | Get system statistics |

### 🔑 Password Recovery (1 endpoint)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/password-recovery-html-content/{email}` | Get password recovery HTML |

**Use Cases:**
- Personal account management
- Session validation
- Basic reporting
- System monitoring

---

## 6. Admin-Only Endpoints

Requires **DoctorOAuth2** authentication with **ADMIN** role.

### 👥 User Administration (10 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/users/` | List all users (doctors/staff/admin) |
| `POST` | `/users/` | Create new user |
| `GET` | `/users/{user_id}` | Get user details |
| `PATCH` | `/users/{user_id}` | Update user information |
| `DELETE` | `/users/{user_id}` | Delete user |
| `PATCH` | `/users/{user_id}/verify` | Verify user account |
| `PATCH` | `/users/{user_id}/activate` | Activate user account |
| `PATCH` | `/users/{user_id}/deactivate` | Deactivate user account |
| `PUT` | `/users/{user_id}/role` | Change user role |
| `GET` | `/users/pending-verification` | List unverified users |

### ⚙️ Clinic Settings (1 endpoint)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `PUT` | `/clinic-settings/` | Update clinic settings |

**Use Cases:**
- User account management
- Role assignments
- Account verification
- System configuration
- Clinic settings management

---

## 7. Quick Lookup Table

### By Feature Category

| Feature | Public | Patient | Doctor | Doctor+Staff | All Auth | Admin |
|---------|:------:|:-------:|:------:|:------------:|:--------:|:-----:|
| **Authentication** | ✅ (7) | - | - | - | ✅ (2) | - |
| **User Management** | ✅ (1) | - | - | - | ✅ (4) | ✅ (10) |
| **Patient Records** | ✅ (1) | ✅ (4) | - | ✅ (10) | - | - |
| **Appointments** | ✅ (3) | ✅ (2) | - | ✅ (8) | - | - |
| **Prescriptions** | - | ✅ (1) | ✅ (5) | - | - | - |
| **Cases** | - | ✅ (1) | ✅ (2) | ✅ (2) | - | - |
| **Medicines** | ✅ (1) | - | - | ✅ (9) | - | - |
| **Follow-ups** | - | - | - | ✅ (8) | - | - |
| **Availability** | ✅ (1) | - | ✅ (11) | - | - | - |
| **Doctor Preferences** | - | - | ✅ (5) | - | - | - |
| **Reports** | ✅ (1) | - | - | - | ✅ (5) | - |
| **Clinic Settings** | ✅ (1) | - | - | - | - | ✅ (1) |
| **Utilities** | - | - | - | - | ✅ (4) | - |

### By HTTP Method

| Method | Public | Patient | Doctor | Doctor+Staff | All Auth | Admin | Total |
|--------|:------:|:-------:|:------:|:------------:|:--------:|:-----:|:-----:|
| **GET** | 5 | 4 | 7 | 27 | 9 | 2 | 54 |
| **POST** | 9 | 0 | 5 | 8 | 8 | 1 | 31 |
| **PUT** | 0 | 1 | 4 | 1 | 0 | 1 | 7 |
| **PATCH** | 0 | 1 | 0 | 2 | 2 | 2 | 7 |
| **DELETE** | 0 | 2 | 7 | 9 | 1 | 3 | 11 |

---

## 8. Permission Matrix

### Patient Permissions

| Action | Own Data | Other Patients |
|--------|:--------:|:--------------:|
| **View Profile** | ✅ | ❌ |
| **Update Profile** | ✅ | ❌ |
| **Delete Account** | ✅ | ❌ |
| **View Appointments** | ✅ | ❌ |
| **Cancel Appointments** | ✅ | ❌ |
| **View Prescriptions** | ✅ | ❌ |
| **View Cases** | ✅ | ❌ |

### Doctor Permissions

| Action | Own Data | Own Patients | All Patients |
|--------|:--------:|:------------:|:------------:|
| **Manage Availability** | ✅ | - | - |
| **Manage Preferences** | ✅ | - | - |
| **View Patients** | - | ✅ | ✅* |
| **Update Patients** | - | ✅ | ✅* |
| **Create Prescriptions** | - | ✅ | ✅ |
| **Manage Cases** | - | ✅ | ✅ |
| **View Appointments** | ✅ | ✅ | ✅* |

*Depends on clinic policy and configuration

### Staff Permissions

| Action | Allowed |
|--------|:-------:|
| **View All Patients** | ✅ |
| **Update Patients** | ✅ |
| **Schedule Appointments** | ✅ |
| **Manage Medicines** | ✅ |
| **View Reports** | ✅ |
| **Manage Users** | ❌ |
| **Change Settings** | ❌ |
| **Create Prescriptions** | ❌ |

### Admin Permissions

| Action | Allowed |
|--------|:-------:|
| **All Staff Permissions** | ✅ |
| **Manage Users** | ✅ |
| **Verify Accounts** | ✅ |
| **Change Roles** | ✅ |
| **Update Settings** | ✅ |
| **View All Data** | ✅ |
| **System Configuration** | ✅ |

---

## 9. Endpoint Access Patterns

### Common Access Patterns

#### Pattern 1: Patient Self-Service
```
Patient Login → View Profile → View Appointments → View Prescriptions → Update Profile
```
**Endpoints Used:**
1. `POST /login/patient-simple`
2. `GET /patients/me`
3. `GET /appointments/patient/my-appointments`
4. `GET /prescriptions/patient/my-prescriptions`
5. `PATCH /patients/me`

#### Pattern 2: Doctor Daily Workflow
```
Doctor Login → Check Schedule → View Today's Appointments → Write Prescriptions → Review Cases
```
**Endpoints Used:**
1. `POST /login/access-token`
2. `GET /availability/my-schedule`
3. `GET /appointments/today`
4. `POST /prescriptions/doctor/`
5. `GET /cases/`

#### Pattern 3: Front Desk Operations (Staff)
```
Staff Login → Search Patient → Update Info → Schedule Appointment → Add Follow-up
```
**Endpoints Used:**
1. `POST /login/access-token`
2. `GET /patients/search`
3. `PUT /patients/{id}`
4. `POST /appointments/book`
5. `POST /follow-ups/`

#### Pattern 4: Admin User Management
```
Admin Login → View Users → Verify New Doctor → Assign Role → Update Settings
```
**Endpoints Used:**
1. `POST /login/access-token`
2. `GET /users/pending-verification`
3. `PATCH /users/{user_id}/verify`
4. `PUT /users/{user_id}/role`
5. `PUT /clinic-settings/`

---

## 10. Security Considerations by Role

### Patient Endpoints Security

**Strengths:**
- Isolated from other patients
- Cannot access doctor or staff functions
- Limited to own data only

**Risks:**
- Simple phone-based authentication
- No email verification
- Predictable credentials (phone = password)

**Recommendations:**
- Implement OTP verification
- Add email as secondary verification
- Force password change on first login

### Doctor Endpoints Security

**Strengths:**
- Email verification required
- Role-based access control
- Separate from patient authentication

**Risks:**
- Can access multiple patient records
- High privilege level
- No MFA for sensitive operations

**Recommendations:**
- Implement MFA for prescription writing
- Add audit logging for patient record access
- Session timeout on inactivity

### Staff Endpoints Security

**Strengths:**
- Cannot create prescriptions
- Cannot manage users
- Limited to operational tasks

**Risks:**
- Broad patient data access
- Can modify patient records
- No granular permissions

**Recommendations:**
- Implement field-level permissions
- Add approval workflow for sensitive changes
- Enhanced audit logging

### Admin Endpoints Security

**Strengths:**
- Full system control
- Can manage all users
- System configuration access

**Risks:**
- No separation of duties
- Single point of failure
- No break-glass mechanism

**Recommendations:**
- Implement dual-admin approval for critical changes
- Add emergency access procedures
- Enhanced monitoring and alerting
- Separate super-admin role

---

## 11. Testing Checklist

### For Each Role, Test:

#### ✅ Positive Tests (Should Succeed)

**Patient:**
- [ ] Can login with valid phone + name
- [ ] Can view own profile
- [ ] Can view own appointments
- [ ] Can cancel own appointments
- [ ] Can update own profile
- [ ] Can change password

**Doctor:**
- [ ] Can login with valid email + password
- [ ] Can manage own availability
- [ ] Can create prescriptions
- [ ] Can view all patients
- [ ] Can view appointments
- [ ] Can manage preferences

**Staff:**
- [ ] Can login with valid credentials
- [ ] Can view all patients
- [ ] Can schedule appointments
- [ ] Can manage medicines
- [ ] Can create follow-ups
- [ ] Can view reports

**Admin:**
- [ ] Can perform all staff operations
- [ ] Can create new users
- [ ] Can verify users
- [ ] Can change roles
- [ ] Can update clinic settings
- [ ] Can deactivate users

#### ❌ Negative Tests (Should Fail)

**Patient:**
- [ ] Cannot access doctor endpoints (403)
- [ ] Cannot view other patients' data (403)
- [ ] Cannot access admin functions (403)
- [ ] Cannot use doctor token (403)

**Doctor:**
- [ ] Cannot access admin-only endpoints (403)
- [ ] Cannot use patient token (403)
- [ ] Cannot access other doctors' preferences (403)

**Staff:**
- [ ] Cannot create prescriptions (403)
- [ ] Cannot manage users (403)
- [ ] Cannot update clinic settings (403)
- [ ] Cannot access doctor preferences (403)

**Cross-Role Tests:**
- [ ] Patient token on doctor endpoint → 403
- [ ] Doctor token on patient endpoint → 403
- [ ] Expired token → 401
- [ ] Invalid token → 401
- [ ] Missing token on protected endpoint → 401

---

## 12. API Integration Guide

### For Frontend Developers

#### Setting Up Authentication

```javascript
// Patient Login
const patientLogin = async (fullName, phone) => {
  const response = await fetch('/login/patient-simple', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ full_name: fullName, phone })
  });
  const data = await response.json();
  localStorage.setItem('patientToken', data.access_token);
  return data;
};

// Doctor/Staff/Admin Login
const doctorLogin = async (email, password) => {
  const response = await fetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  localStorage.setItem('doctorToken', data.access_token);
  localStorage.setItem('userRole', data.user.role);
  return data;
};
```

#### Making Authenticated Requests

```javascript
// Patient Request
const getMyAppointments = async () => {
  const token = localStorage.getItem('patientToken');
  const response = await fetch('/appointments/patient/my-appointments', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Doctor Request
const getTodayAppointments = async () => {
  const token = localStorage.getItem('doctorToken');
  const response = await fetch('/appointments/today', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

#### Role-Based UI Rendering

```javascript
const renderNavigation = (userRole) => {
  const navItems = {
    patient: [
      { path: '/profile', label: 'My Profile' },
      { path: '/appointments', label: 'My Appointments' },
      { path: '/prescriptions', label: 'My Prescriptions' }
    ],
    doctor: [
      { path: '/dashboard', label: 'Dashboard' },
      { path: '/schedule', label: 'My Schedule' },
      { path: '/patients', label: 'Patients' },
      { path: '/prescriptions', label: 'Prescriptions' }
    ],
    staff: [
      { path: '/dashboard', label: 'Dashboard' },
      { path: '/patients', label: 'Patients' },
      { path: '/appointments', label: 'Appointments' },
      { path: '/medicines', label: 'Medicines' }
    ],
    admin: [
      { path: '/dashboard', label: 'Dashboard' },
      { path: '/users', label: 'User Management' },
      { path: '/patients', label: 'Patients' },
      { path: '/settings', label: 'Settings' }
    ]
  };
  
  return navItems[userRole] || [];
};
```

### For Backend Developers

#### Implementing Role Checks

```python
from fastapi import Depends, HTTPException, status
from typing import List

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# Usage examples:
@router.get("/users/")
async def list_users(
    current_user: User = Depends(require_roles(["admin"]))
):
    # Admin only endpoint
    pass

@router.get("/patients/")
async def list_patients(
    current_user: User = Depends(require_roles(["doctor", "staff", "admin"]))
):
    # Doctor, staff, or admin can access
    pass
```

---

## 13. Common Integration Scenarios

### Scenario 1: Patient Portal
**Endpoints Needed:**
- `POST /login/patient-simple` - Login
- `GET /patients/me` - Get profile
- `GET /appointments/patient/my-appointments` - View appointments
- `GET /prescriptions/patient/my-prescriptions` - View prescriptions
- `PATCH /patients/me` - Update profile

### Scenario 2: Doctor Dashboard
**Endpoints Needed:**
- `POST /login/access-token` - Login
- `GET /availability/my-schedule` - View schedule
- `GET /appointments/today` - Today's appointments
- `GET /patients/{id}` - Patient details
- `POST /prescriptions/doctor/` - Write prescription
- `GET /cases/` - View cases

### Scenario 3: Front Desk Application
**Endpoints Needed:**
- `POST /login/access-token` - Login
- `GET /patients/search` - Find patient
- `POST /patients/` - Register new patient
- `POST /appointments/book` - Book appointment
- `GET /appointments/available-slots/{doctor_id}` - Check availability
- `POST /follow-ups/` - Schedule follow-up

### Scenario 4: Admin Panel
**Endpoints Needed:**
- `POST /login/access-token` - Login
- `GET /users/` - List all users
- `POST /users/` - Create user
- `PATCH /users/{user_id}/verify` - Verify user
- `PUT /users/{user_id}/role` - Change role
- `PUT /clinic-settings/` - Update settings
- `GET /reports/custom` - Generate reports

---

## 14. Error Codes Reference

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| **200** | Success | Request completed successfully |
| **201** | Created | Resource created successfully |
| **400** | Bad Request | Invalid input data |
| **401** | Unauthorized | Missing or invalid token |
| **403** | Forbidden | Wrong role or insufficient permissions |
| **404** | Not Found | Resource doesn't exist |
| **422** | Validation Error | Input validation failed |
| **500** | Server Error | Internal server error |

### Role-Specific Error Examples

**Patient using doctor endpoint:**
```json
{
  "detail": "Access denied. This endpoint requires DoctorOAuth2 authentication."
}
```

**Staff trying to access admin endpoint:**
```json
{
  "detail": "Access denied. Required roles: admin"
}
```

**Expired token:**
```json
{
  "detail": "Token has expired"
}
```

---

## 15. Summary & Best Practices

### Key Takeaways

1. **Always use the correct authentication**
   - Patient endpoints require PatientBearer token
   - Doctor/Staff/Admin endpoints require DoctorOAuth2 token
   - Tokens are NOT interchangeable

2. **Respect role boundaries**
   - Don't try to access endpoints your role doesn't permit
   - Implement proper role checks in your UI
   - Handle 403 errors gracefully

3. **Token management**
   - Store tokens securely
   - Include token in Authorization header
   - Handle token expiration (1 hour)
   - Implement re-login flow

4. **Error handling**
   - Always check for 401 (redirect to login)
   - Handle 403 (show permission error)
   - Validate input before sending (avoid 422)

### Development Best Practices

**Do:**
✅ Check user role before showing UI elements  
✅ Handle token expiration gracefully  
✅ Use appropriate error messages  
✅ Implement proper loading states  
✅ Test with different role accounts  
✅ Log authentication failures  

**Don't:**
❌ Hard-code role checks in UI only  
❌ Expose sensitive endpoints publicly  
❌ Share tokens between users  
❌ Store tokens in insecure locations  
❌ Ignore 403 errors  
❌ Mix patient and doctor authentication  

---

## Appendix: Complete Endpoint List

See attached JSON file `endpoints_by_role.json` for complete machine-readable endpoint list with full details including request/response schemas.

---

**Document Version:** 1.0  
**Last Updated:** January 31, 2026  
**API Version:** 1.0.0  
**Total Endpoints Documented:** 110
