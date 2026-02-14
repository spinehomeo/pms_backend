# .__init__.py
# This file imports .in the correct order to avoid circular imports

# First import .without relationships
from .users_model import UserBase
from .patients_model import PatientBase, PatientGender
from .cases_model import PatientCaseBase
from .prescriptions_model import PrescriptionBase, PrescriptionType
from .medicines_model import DoctorMedicineStockBase, FormEnum, ScaleEnum
from .appointments_model import AppointmentBase, AppointmentStatus
from .followups_model import FollowUpBase
from .doctor_availability_model import DoctorAvailabilityBase, DayOfWeek

# Then import the table .(in dependency order)
from .users_model import User
from .patients_model import Patient
from .cases_model import PatientCase
from .medicines_model import Medicine, DoctorMedicineStock
from .prescriptions_model import Prescription, PrescriptionMedicine
from .appointments_model import Appointment
from .followups_model import FollowUp
from .doctor_availability_model import DoctorAvailability
from .doctor_preferences_model import DoctorCaseFieldPreference, DoctorCaseTemplate

# Web content models
from .web_content_model import (
    AboutDoctor, Qualification, Specialization,
    HeroSection, Credential,
    ServicesAndTreatments, Service,
    PatientSuccessStories, Testimonial,
    ContactInformation,
)

__all__ = [
    # Base models
    "UserBase", "PatientBase", "PatientGender", "PatientCaseBase", 
    "PrescriptionBase", "PrescriptionType", 
    "DoctorMedicineStockBase", "FormEnum", "ScaleEnum",
    "AppointmentBase", "AppointmentStatus", "FollowUpBase",
    "DoctorAvailabilityBase", "DayOfWeek",
    
    # Table models
    "User", "Patient", "PatientCase", "Medicine", 
    "DoctorMedicineStock", "Prescription", "PrescriptionMedicine",
    "Appointment", "FollowUp", "DoctorAvailability",
    "DoctorCaseFieldPreference", "DoctorCaseTemplate",
    
    # Web content models
    "AboutDoctor", "Qualification", "Specialization",
    "HeroSection", "Credential",
    "ServicesAndTreatments", "Service",
    "PatientSuccessStories", "Testimonial",
    "ContactInformation",
]