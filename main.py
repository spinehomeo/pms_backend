import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import settings

import os
import sys
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("Parent contents:", os.listdir('..'))



print("=== DEBUG INFO ===")
print("Current dir:", os.getcwd())
print("Python path:", sys.path)
print("Files in current dir:", os.listdir('.'))
if 'api' in os.listdir('.'):
    print("✓ 'api' directory exists")
else:
    print("✗ 'api' directory NOT found!")
print("==================")

# Debug for deployment
print("=== NORTHFLANK DEBUG ===")
print("Working directory:", os.getcwd())
print("Python path:", sys.path)
print("Listing current directory:", os.listdir('.'))
print("=======================")


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

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
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



