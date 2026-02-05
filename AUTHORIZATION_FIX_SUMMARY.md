# Authorization Logic Fix: Self-Service Endpoints

## The Problem

The API had a **mismatch between Swagger documentation and actual authorization logic**:

### What Swagger Said
```
👤 Access: Doctor, Staff, Admin
```

### What Actually Happened
All endpoints (even `/users/me`, `/users/signup`, etc.) were protected by:
```python
admin_router = APIRouter(
    prefix="/users",
    dependencies=[Security(get_current_active_superuser)]  # ← Blocked everyone except admin
)

router = admin_router  # ← All endpoints used this admin-only router
```

### Result
Doctor token → 403 Forbidden (even though Swagger said it should work)

---

## Root Cause

The file structure was:
```
1. Create admin_router with @Security(get_current_active_superuser)
2. Add admin endpoints (@admin_router.get("/"))
3. Export: router = admin_router
4. Add self-service endpoints using @router.patch("/me")  ← Wrong! Still admin-only
5. Add public endpoints using @router.post("/signup")    ← Wrong! Still admin-only
```

This meant:
- Self-service endpoints inherited admin-only dependency
- Public endpoints were blocked when they shouldn't be
- Authorization ≠ Documentation

---

## The Solution

### 1. Split Routers by Authorization Level

**Before:**
```python
admin_router = APIRouter(
    prefix="/users",
    dependencies=[Security(get_current_active_superuser)]
)

router = admin_router  # ← All endpoints here are admin-only
```

**After:**
```python
# Router for admin-only operations (system-level CRUD)
admin_router = APIRouter(
    prefix="/users",
    dependencies=[Security(get_current_active_superuser)]
)

# Router for self-service + public endpoints (no router-level auth)
self_service_router = APIRouter(prefix="/users")

# Main router that combines both (for api/router.py)
router = APIRouter(prefix="/users")
```

### 2. Assign Endpoints to Correct Router

**Admin-Only Endpoints (use admin_router):**
- `GET /users/` → List all users
- `POST /users/` → Create user
- `GET /users/{user_id}` → Get user by ID
- `PATCH /users/{user_id}` → Update user
- `DELETE /users/{user_id}` → Delete user

**Self-Service Endpoints (use self_service_router):**
- `GET /users/me` → Uses `current_user: CurrentUser` (authenticates)
- `PATCH /users/me` → Uses `current_user: CurrentUser`
- `DELETE /users/me` → Uses `current_user: CurrentUser`
- `PATCH /users/me/password` → Uses `current_user: CurrentUser`
- `GET /users/me/stats` → Uses `current_user: CurrentUser`

**Public Endpoints (use self_service_router):**
- `POST /users/signup` → Public signup (no auth)
- `POST /users/patients/register-simple` → Public (no auth)
- `POST /users/patients/quick-access` → Public (no auth)

**Admin/Staff Listing (use self_service_router with role check):**
- `GET /users/doctors/list` → Uses `dependencies=[Security(require_roles("admin", "staff"))]`

### 3. Combine Routers for Export

```python
# At end of file:
router.include_router(admin_router)
router.include_router(self_service_router)
```

This way:
- `api/router.py` includes only one router: `users.router`
- That router contains both admin and self-service endpoints
- Each endpoint has appropriate authorization

---

## Authentication Dependency Explained

### `CurrentUser = Annotated[User, Depends(get_current_user)]`

When you add `current_user: CurrentUser` to a function signature:

```python
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user
```

FastAPI automatically:
1. ✅ Requires a valid OAuth2 token (DoctorOAuth2)
2. ✅ Decodes and validates the JWT
3. ✅ Looks up the User in database
4. ✅ Checks if user is active
5. ✅ Raises 401 if any of above fails
6. ✅ Passes the User object to your function

**You don't need to do anything else** — just having `current_user: CurrentUser` as a parameter handles auth automatically.

---

## New Dependency: `require_roles()`

Added to `api/deps.py`:

```python
def require_roles(*allowed_roles: str):
    """
    Factory function to create a role-checking dependency.
    
    Usage:
        @router.get("/doctors/list")
        def list_doctors(
            current_user: User = Depends(require_roles("admin", "staff"))
        ):
            return doctors
    """
    def role_checker(
        current_user: User = Security(get_current_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="...")
        return current_user
    
    return role_checker
```

**How it works:**
- Takes multiple role names as arguments
- Returns a dependency function
- The dependency checks if user's role is in the allowed list
- Raises 403 if not

**Usage example:**
```python
@router.get("/doctors/list", dependencies=[Security(require_roles("admin", "staff"))])
def list_doctors(...):
    """Can only be called by admin or staff"""
```

---

## Before & After: What Changed

### Endpoint: GET /users/me

**Before:**
```python
@router.get("/me")  # ← router = admin_router (WRONG!)
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user

# Behavior: ❌ Only admin could call (403 for doctors)
```

**After:**
```python
@self_service_router.get("/me")  # ← Correct router
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user

# Behavior: ✅ Any authenticated user can call
# Doctor token → Returns doctor's profile ✓
# Staff token → Returns staff's profile ✓
# Admin token → Returns admin's profile ✓
# No token → 401 Unauthorized ✓
```

### Endpoint: GET /users/doctors/list

**Before:**
```python
@router.get("/doctors/list")  # ← router = admin_router
def list_doctors(...) -> Any:
    return doctors

# Behavior: ❌ Only admin could call (403 for staff)
# But Swagger said: "Admin, Staff"
```

**After:**
```python
@self_service_router.get(
    "/doctors/list",
    dependencies=[Security(require_roles("admin", "staff"))]
)
def list_doctors(...) -> Any:
    return doctors

# Behavior: ✅ Admin or Staff can call
# Admin token → Returns all doctors ✓
# Staff token → Returns all doctors ✓
# Doctor token → 403 Forbidden ✓
# No token → 401 Unauthorized ✓
```

---

## How This Aligns with Swagger Tags

The Swagger documentation we created earlier is now **actually enforced** in the code:

| Swagger Tag | Swagger Says | Actual Implementation |
|---|---|---|
| 🛡️ Admin | Admin only | `admin_router` with `@Security(get_current_active_superuser)` |
| 👤 Self-Service | Doctor/Staff/Admin | `self_service_router` with `current_user: CurrentUser` |
| 🧑‍⚕️ Doctor | Doctor only | `self_service_router` with `require_roles("doctor")` |
| 🩺 Listing | Admin/Staff | `self_service_router` with `require_roles("admin", "staff")` |
| 📝 Registration | Public | `self_service_router` with no dependencies |

**No more mismatches!** ✅

---

## Testing the Fix

### Before Fix
```bash
# Doctor tries to access /users/me
Token: doctor_token
Response: 403 Forbidden "The user doesn't have enough privileges"
```

### After Fix
```bash
# Doctor tries to access /users/me
Token: doctor_token
Response: 200 OK + { id, email, name, role: "doctor" }
```

---

## Files Changed

1. **api/deps.py**
   - Added `require_roles()` factory function
   - Export in imports if needed

2. **routes/users.py**
   - Split `admin_router` from `self_service_router`
   - Moved all non-admin endpoints to `self_service_router`
   - Added `require_roles("admin", "staff")` to `/doctors/list`
   - Combined both routers at end: `router.include_router(admin_router)`

---

## Summary

✅ **What was fixed:**
- Swagger documentation now matches actual authorization
- Doctor tokens work for self-service endpoints
- Role checking works for restricted endpoints
- Public endpoints are truly public

✅ **How it works:**
- Admin endpoints on `admin_router` (admin-only by router dependency)
- Self-service endpoints on `self_service_router` (auth at endpoint level)
- Both combined into single `router` for export

✅ **Result:**
- 403 errors only when actually unauthorized
- Swagger descriptions match actual behavior
- Code is cleaner and more maintainable

---

**Status:** ✅ Authorization logic fixed and aligned with Swagger documentation
