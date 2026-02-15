import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.router import api_router
from core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    tags = getattr(route, "tags", None) or []
    tag = tags[0] if len(tags) > 0 else "default"
    name = getattr(route, "name", None) or "endpoint"
    return f"{tag}-{name}"


# Initialize limiter at module level
limiter = Limiter(key_func=get_remote_address)

# Initialize Sentry if configured
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        enable_tracing=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
    )

# ============================================================================
# OpenAPI Tags Metadata - Role-Based Organization
# ============================================================================
# This creates a legend in Swagger that explains the role hierarchy.
# Tags are organized by access level to make authorization obvious at a glance.
# ============================================================================
tags_metadata = [
    {
        "name": "🛡️ Admin | User Management",
        "description": """
        **Who:** ADMIN only

        System-level user management endpoints. Admins can create, read, update, and delete 
        any user (doctor, staff, admin). Regular doctors cannot access these endpoints.

        **Authentication:** DoctorOAuth2 (Admin role required)
        """
    },
    {
        "name": "👤 Self-Service | User Profile",
        "description": """
        **Who:** Doctor, Staff, Admin

        Endpoints for authenticated users to manage their own profile. Each user can only 
        access their own profile (GET /users/me, PATCH /users/me, DELETE /users/me).

        **Authentication:** DoctorOAuth2
        """
    },
    {
        "name": "👤 Self-Service | Password",
        "description": """
        **Who:** Doctor, Staff, Admin

        Password management for authenticated users. Users can only change their own password.

        **Authentication:** DoctorOAuth2
        """
    },
    {
        "name": "🧑‍⚕️ Doctor | Statistics",
        "description": """
        **Who:** Doctor (staff & admin can auth, but endpoint is doctor-specific)

        Doctor-only statistics endpoints. Shows appointments, cases, prescriptions, 
        medicine stock, and other practice metrics.

        **Authentication:** DoctorOAuth2
        """
    },
    {
        "name": "📝 Registration | User Signup",
        "description": """
        **Who:** Doctor, Staff (public signup)

        User registration endpoint for creating new doctor or staff accounts. 
        Does NOT create patient accounts.

        **Authentication:** Public (or optional pre-approval)
        """
    },
    {
        "name": "🧍 Registration | Patient",
        "description": """
        **Who:** Frontend, Staff, Public

        Patient registration endpoints. These do NOT create User accounts; they create Patient records.
        Phone number serves as the patient's password for simple login flows.

        **Authentication:** Public or Staff-authenticated
        """
    },
    {
        "name": "🩺 Listing | Doctor Directory",
        "description": """
        **Who:** Admin, Staff

        Internal doctor listing for dashboards and staff tools. 
        Public users should use /public/doctors instead.

        **Authentication:** DoctorOAuth2 (Admin or Staff role)
        """
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
## 🔐 Authentication Guide

This API uses **two completely separate authentication systems** for two different user domains:

### 🧑‍⚕️ Doctor / Staff / Administrator
- **Authentication type:** OAuth2 Password Bearer
- **Swagger scheme name:** `DoctorOAuth2`
- **Login endpoint:** `POST /login/access-token`
- **Token format:** JWT with `"entity": "user"` claim
- **Use this for:** Doctor, staff, and admin management endpoints
- **Swagger:** Use the "Authorize" button → enter username + password

### 🧍 Patient
- **Authentication type:** HTTP Bearer (JWT)
- **Swagger scheme name:** `PatientBearer`  
- **Login endpoint:** `POST /login/patient-simple`
- **Token format:** JWT with `"entity": "patient"` claim
- **Use this for:** Patient profile, appointments, and related endpoints
- **Swagger:** Use the "Authorize" button → paste entire JWT token

### ⚠️ CRITICAL NOTES
- **Tokens are NOT interchangeable.** Using a patient token on a doctor endpoint will fail with 403 Forbidden.
- Each endpoint explicitly declares which auth method it requires.
- Swagger will only send the correct token to endpoints that accept it.
- Patient tokens are stored in the **Patient** table.
- Doctor/staff/admin tokens are stored in the **User** table.
- **Note:** Authorization uses roles (ADMIN, DOCTOR, STAFF) stored in JWT. Scope-based access control is not used.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    generate_unique_id_function=custom_generate_unique_id,
    swagger_ui_parameters={"swaggerOptions": {"persistAuthorization": True}},
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeFlow": False
    }
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add rate limiting middleware
app.add_middleware(SlowAPIMiddleware)

# Set all CORS enabled origins
# Configure allowed origins for cross-origin requests from frontend applications
allowed_origins = [
    # Production
    "https://pms-frontend-ten.vercel.app",
    "https://site--spinehomeo-backend--sddjlksrw789.code.run",  # Live backend (for development reference)
    "https://herbaldoc.netlify.app",
    # Development
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:3000",
]

# Add any additional origins from environment if configured
extra_origins = settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS else []
if isinstance(extra_origins, str):
    allowed_origins.extend([origin.strip() for origin in extra_origins.split(",")])
elif isinstance(extra_origins, list):
    allowed_origins.extend(extra_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["Content-Length", "Content-Type"],
    max_age=3600,
)

app.include_router(api_router, prefix=settings.API_V1_STR)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )

    # =========================================================================
    # CONFIGURE SECURITY SCHEMES (CLEAN UP AUTO-GENERATED ONES)
    # =========================================================================
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})

    # Remove auto-generated OAuth2PasswordBearer to avoid duplication
    # (FastAPI auto-generates one, but we want only our explicit ones)
    security_schemes.clear()

    # Doctor/Staff/Admin: OAuth2 Password Bearer
    security_schemes["DoctorOAuth2"] = {
        "type": "oauth2",
        "flows": {
            "password": {
                "tokenUrl": f"{settings.API_V1_STR}/login/access-token",
                "scopes": {
                    "read": "Read access",
                    "write": "Write access"
                }
            }
        },
        "description": "OAuth2 password flow for doctors, staff, and administrators. Use /login/access-token endpoint."
    }

    # Patient: HTTP Bearer JWT
    security_schemes["PatientBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT Bearer token for patient authentication. Use /login/patient-simple endpoint to obtain token."
    }

    # =========================================================================
    # SET TAG DESCRIPTIONS
    # =========================================================================
    openapi_schema["tags"] = [
        {
            "name": "🧑‍⚕️ Doctor / Staff / Admin",
            "description": "Endpoints for doctors, staff, and administrators only. Requires **DoctorOAuth2** authentication. Tokens are issued via `/login/access-token`."
        },
        {
            "name": "🧍 Patient",
            "description": "Endpoints for authenticated patients only. Requires **PatientBearer** JWT token. Tokens are issued via `/login/patient-simple`."
        },
        {
            "name": "🌍 Public",
            "description": "Publicly accessible endpoints. No authentication required."
        },
        {
            "name": "🔑 Authentication",
            "description": "Authentication endpoints. Choose the appropriate login based on your user type."
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
@limiter.limit("100/minute")
def health(request: Request):
    """Health check endpoint"""
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/doc")
@limiter.limit("100/minute")
def doc(request: Request):
    """Documentation endpoint"""
    return {"doc": "alive", "openapi": f"{settings.API_V1_STR}/openapi.json"}


# Optional: Add a custom rate limit exceeded response
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "code": "rate_limit_exceeded",
        },
    )