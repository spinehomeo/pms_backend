import sentry_sdk
from fastapi import FastAPI, Request
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

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add rate limiting middleware
app.add_middleware(SlowAPIMiddleware)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://pms-frontend-ten.vercel.app",
            "http://localhost:5173",
            "http://localhost:8080",
            "https://475ce336-56fd-48e9-ac15-b78dbe63fed9.lovableproject.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


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