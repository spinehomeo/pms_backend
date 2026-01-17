# .__init__.py
# This file imports .in the correct order to avoid circular imports

# First import .without relationships
from .users_model import UserBase
from .patients_model import PatientBase, PatientGender
from .cases_model import PatientCaseBase
from .prescriptions_model import PrescriptionBase, PrescriptionType
from .medicines_model import MedicineMasterBase, DoctorMedicineStockBase, MedicineForm, PotencyScale
from .appointments_model import AppointmentBase, AppointmentStatus
from .followups_model import FollowUpBase
from .doctor_availability_model import DoctorAvailabilityBase, DayOfWeek

# Then import the table .(in dependency order)
from .users_model import User
from .patients_model import Patient
from .cases_model import PatientCase
from .medicines_model import MedicineMaster, DoctorMedicineStock
from .prescriptions_model import Prescription, PrescriptionMedicine
from .appointments_model import Appointment
from .followups_model import FollowUp
from .doctor_availability_model import DoctorAvailability

__all__ = [
    # Base models
    "UserBase", "PatientBase", "PatientGender", "PatientCaseBase", 
    "PrescriptionBase", "PrescriptionType", "MedicineMasterBase", 
    "DoctorMedicineStockBase", "MedicineForm", "PotencyScale",
    "AppointmentBase", "AppointmentStatus", "FollowUpBase",
    "DoctorAvailabilityBase", "DayOfWeek",
    
    # Table models
    "User", "Patient", "PatientCase", "MedicineMaster", 
    "DoctorMedicineStock", "Prescription", "PrescriptionMedicine",
    "Appointment", "FollowUp", "DoctorAvailability",
]