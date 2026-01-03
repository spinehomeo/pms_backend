import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.extension import _rate_limit_exceeded_handler

from api.router import api_router
from core.config import settings



def custom_generate_unique_id(route: APIRoute) -> str:
    tags = getattr(route, "tags", None) or []
    tag = tags[0] if len(tags) > 0 else "default"
    name = getattr(route, "name", None) or "endpoint"
    return f"{tag}-{name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Register slowapi limiter (optional, requires slowapi installed)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.all_cors_origins,
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
def health():
    return {"status": "ok"}

@app.get("/doc")
def doc():
    return {"doc": "alive"}



