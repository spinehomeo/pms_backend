# .__init__.py
# This file imports .in the correct order to avoid circular imports

# First import .without relationships
from .users_model import UserBase
from .patients_model import PatientBase
from .cases_model import PatientCaseBase
from .prescriptions_model import PrescriptionBase
from .medicines_model import FormEnum, ScaleEnum, ManufacturerEnum
from .appointments_model import AppointmentBase
from .followups_model import FollowUpBase
from .doctor_availability_model import DoctorAvailabilityBase
from .doctor_availability_exception_model import DoctorAvailabilityExceptionBase
from .enum_option_model import EnumTypeBase, EnumOptionBase, DoctorEnumPreferenceBase

# Then import the table .(in dependency order)
from .users_model import User
from .patients_model import Patient
from .cases_model import PatientCase
from .medicines_model import Medicine, DoctorMedicinePreference
from .prescriptions_model import Prescription, PrescriptionMedicine
from .appointments_model import Appointment
from .followups_model import FollowUp
from .doctor_availability_model import DoctorAvailability
from .doctor_availability_exception_model import DoctorAvailabilityException
from .doctor_preferences_model import DoctorCaseFieldPreference, DoctorCaseTemplate
from .enum_option_model import EnumType, EnumOption, DoctorEnumPreference

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
    "UserBase", "PatientBase", "PatientCaseBase", 
    "PrescriptionBase",
    "FormEnum", "ScaleEnum", "ManufacturerEnum",
    "AppointmentBase", "FollowUpBase",
    "DoctorAvailabilityBase",
    "DoctorAvailabilityExceptionBase",
    "EnumTypeBase", "EnumOptionBase", "DoctorEnumPreferenceBase",
    
    # Table models
    "User", "Patient", "PatientCase", "Medicine", 
    "DoctorMedicinePreference", "Prescription", "PrescriptionMedicine",
    "Appointment", "FollowUp", "DoctorAvailability", "DoctorAvailabilityException",
    "DoctorCaseFieldPreference", "DoctorCaseTemplate",
    "EnumType", "EnumOption", "DoctorEnumPreference",
    
    # Web content models
    "AboutDoctor", "Qualification", "Specialization",
    "HeroSection", "Credential",
    "ServicesAndTreatments", "Service",
    "PatientSuccessStories", "Testimonial",
    "ContactInformation",
]