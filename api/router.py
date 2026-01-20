from fastapi import APIRouter

from routes import (
    appointments,
    cases,
    doctor_availability,
    followups,
    login,
    medicines,
    patients,
    prescriptions,
    private,
    reports,
    users,
    utils_routes,
)
from core.config import settings

api_router = APIRouter()

# Core routers
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(doctor_availability.router)
api_router.include_router(utils_routes.router)

# Feature routers
api_router.include_router(appointments.router)
api_router.include_router(cases.router)
api_router.include_router(followups.router)
api_router.include_router(medicines.router)
api_router.include_router(patients.router)
api_router.include_router(prescriptions.router)
api_router.include_router(reports.router)

# Dev-only router
if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
