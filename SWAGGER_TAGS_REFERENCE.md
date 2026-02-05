# Swagger Tags Implementation Guide

## ✅ Implementation Complete: User Management Module

The `/users/*` endpoints have been updated with role-based Swagger tags for maximum clarity.

---

## 🎯 What Was Done

### 1. Global Tag Metadata (main.py)
Added `tags_metadata` list to FastAPI app initialization. This creates a **legend** at the top of Swagger showing:
- Which roles access which tags
- Authentication requirements
- Purpose of each tag group

**Tags defined:**
- 🛡️ Admin | User Management
- 👤 Self-Service | User Profile
- 👤 Self-Service | Password
- 🧑‍⚕️ Doctor | Statistics
- 📝 Registration | User Signup
- 🧍 Registration | Patient
- 🩺 Listing | Doctor Directory

### 2. Endpoint-Level Tags (routes/users.py)
Every endpoint now has:
- **Tag:** Role-prefixed for quick visual identification
- **Access Block:** 🔐 or 🧑‍⚕️ emoji + role info
- **Full Description:** Authentication type, required fields, behavior, restrictions

---

## 📋 Tag Structure Reference

### Standard Endpoint Documentation Pattern

```python
@router.get(
    "/endpoint-path",
    tags=["🛡️ Admin | User Management"],  # ← Role-prefixed tag
    response_model=ResponseModel
)
def endpoint_function(...) -> Any:
    """
    🔐 **Access:** [ROLE DESCRIPTION]
    
    **Authentication:** [Auth method: DoctorOAuth2 / PatientBearer / Public]
    
    [Detailed description of what this endpoint does]
    
    **Required fields:** [List fields]
    
    **Returns:** [What is returned]
    
    **Restrictions:** [Any limitations]
    """
```

---

## 🏷️ Available Tags (Copy-Paste Ready)

### Admin-Only Operations
```python
tags=["🛡️ Admin | User Management"]
```

### Self-Service (Doctor/Staff/Admin - Own Profile)
```python
tags=["👤 Self-Service | User Profile"]        # For profile get/update/delete
tags=["👤 Self-Service | Password"]            # For password change
```

### Doctor-Specific
```python
tags=["🧑‍⚕️ Doctor | Statistics"]
tags=["🧑‍⚕️ Doctor | Appointments"]  # Example for future use
```

### User Registration (NOT patient)
```python
tags=["📝 Registration | User Signup"]
```

### Patient Registration/Access
```python
tags=["🧍 Registration | Patient"]
tags=["🧍 Patient | Profile"]                  # Example for future use
tags=["🧍 Patient | Appointments"]             # Example for future use
```

### Listing/Directory
```python
tags=["🩺 Listing | Doctor Directory"]
```

### Public Endpoints
```python
tags=["🌍 Public | Doctors"]                   # Example: GET /public/doctors
tags=["🌍 Public | Appointments"]              # Example: Public appointment search
```

---

## 🔧 How to Extend Tags for Other Routes

### Step 1: Add to tags_metadata (main.py)
If you create NEW tag categories, add them to the `tags_metadata` list in main.py:

```python
{
    "name": "🧑‍⚕️ Doctor | Appointments",  # Unique tag name
    "description": """
    **Who:** Doctor, Staff

    Doctor-specific appointment management endpoints.

    **Authentication:** DoctorOAuth2
    """
}
```

### Step 2: Apply to Endpoints
Use the tag in route decorators:

```python
@router.get(
    "/appointments",
    tags=["🧑‍⚕️ Doctor | Appointments"],
    response_model=AppointmentList
)
def list_doctor_appointments(...) -> Any:
    """
    🧑‍⚕️ **Access:** Doctor (owns appointments)

    **Authentication:** DoctorOAuth2
    
    List all appointments for the current doctor...
    """
```

---

## 📝 Access Block Examples

### Admin-Only (System Control)
```
🔐 **Access:** ADMIN only

**Authentication:** DoctorOAuth2 (Admin role required)
```

### Doctor-Only (Domain Specific)
```
🧑‍⚕️ **Access:** Doctor only

**Authentication:** DoctorOAuth2 (Doctor role required)
```

### Self-Service (Own Resource)
```
👤 **Access:** Doctor, Staff, Admin (own profile only)

**Authentication:** DoctorOAuth2
```

### Patient (Separate Auth System)
```
🧍 **Access:** Patient (authenticated)

**Authentication:** PatientBearer (JWT from /login/patient-simple)
```

### Public (No Auth)
```
🌍 **Access:** Public (no authentication)

**Authentication:** None required
```

---

## 📚 Example: Updating appointments.py

**Current state (if not tagged):**
```python
@router.get("/")
def list_appointments(...) -> Any:
    """
    List appointments.
    """
```

**After update:**
```python
@router.get(
    "/",
    tags=["🧑‍⚕️ Doctor | Appointments"]
)
def list_appointments(...) -> Any:
    """
    🧑‍⚕️ **Access:** Doctor (own appointments), Patient (own appointments)

    **Authentication:** DoctorOAuth2 or PatientBearer

    List all appointments for the current user (doctor or patient).

    **Query Parameters:**
    - `skip`: Records to skip (default: 0)
    - `limit`: Records to return (default: 100)

    **Returns:**
    - Doctor: All their appointments (all patients)
    - Patient: Their own appointments

    **Filtering:** Automatically filtered by current user's role
    """
```

---

## ✨ Why This Matters

### Before (Confusing)
```
Swagger shows:
  GET  /users/
  GET  /users/me
  GET  /users/{id}
  ...
  
👁️ Developer doesn't know which endpoint needs which auth
```

### After (Clear)
```
Swagger shows:
  🛡️ Admin | User Management
    GET  /users/        (ADMIN only)
    POST /users/        (ADMIN only)
    GET  /users/{id}    (ADMIN only)
  
  👤 Self-Service | User Profile
    GET  /users/me      (Doctor/Staff/Admin - own)
    PATCH /users/me     (Doctor/Staff/Admin - own)
    
  🧍 Registration | Patient
    POST /patients/register-simple
    POST /patients/quick-access
    
👁️ Developer immediately sees role & auth requirements
```

---

## 🚀 Benefits

✅ **Frontend developers** see auth requirements immediately  
✅ **QA engineers** spot authorization gaps quickly  
✅ **New team members** understand API structure in minutes  
✅ **API consumers** understand which endpoints they can use  
✅ **Documentation** becomes self-explanatory through Swagger  

---

## 📋 Checklist for New Endpoints

When adding new endpoints, ask:

- [ ] What role(s) can access this?
- [ ] What auth method is required?
- [ ] Is it admin-only, self-service, or public?
- [ ] What's the appropriate emoji prefix?
- [ ] Should I create a new tag or use existing?
- [ ] Have I added the access block to docstring?
- [ ] Is the description clear for frontend devs?

---

## 🔗 Related Files

- **main.py** - Contains `tags_metadata` definition
- **routes/users.py** - Complete example with all tag types
- **routes/** - Other files to update with same pattern

---

## 💡 Pro Tips

1. **Consistency** - Use the same tag for all related endpoints
2. **Emoji** - Keep emoji-first for visual scanning
3. **Pipe separator** - Use format "🔐 Role | Feature"
4. **Docstring** - Start with access block, then details
5. **Test in Swagger** - Visit `/docs` to verify tags appear correctly

---

## 🎓 Next Steps

Apply this pattern to:
1. `routes/appointments.py` - Doctor & Patient appointments
2. `routes/patients.py` - Patient data (Staff/Doctor access)
3. `routes/login.py` - Both DoctorOAuth2 and PatientBearer flows
4. Other route files following the same pattern

---

Generated: 2025-02-05  
Pattern: Role-Based Swagger Tag Organization  
Status: ✅ User Management Module Complete
