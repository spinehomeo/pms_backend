from fastapi import APIRouter

from routes import (
    appointments,
    cases,
    doctor_availability,
    doctor_preferences,
    enums,
    finance,
    followups,
    login,
    medicines,
    onsite_consultation,
    onsite_patient,
    patients,
    prescriptions,
    private,
    public,
    reports,
    users,
    utils_routes,
    web_content,
)
from core.config import settings

api_router = APIRouter()

# Core routers
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(doctor_availability.router)
api_router.include_router(public.router)
api_router.include_router(utils_routes.router)
api_router.include_router(enums.router)

# Feature routers
api_router.include_router(appointments.router)
api_router.include_router(cases.router)
api_router.include_router(doctor_preferences.router)
api_router.include_router(finance.router)
api_router.include_router(followups.router)
api_router.include_router(medicines.router)
api_router.include_router(onsite_patient.router)
api_router.include_router(onsite_consultation.router)
api_router.include_router(patients.router)
api_router.include_router(prescriptions.router)
api_router.include_router(reports.router)
api_router.include_router(web_content.router)

# Dev-only router
if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
