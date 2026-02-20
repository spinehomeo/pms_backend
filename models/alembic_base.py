from sqlmodel import SQLModel

# Import model classes so their table metadata is registered with SQLModel.metadata
from models.users_model import User
from models.prescriptions_model import Prescription, PrescriptionMedicine
from models.patients_model import Patient
from models.medicines_model import Medicine, DoctorMedicinePreference
from models.followups_model import FollowUp
from models.cases_model import PatientCase
from models.appointments_model import Appointment
from models.enum_option_model import EnumType, EnumOption, DoctorEnumPreference

# # Alembic / SQLModel target metadata
# target_metadata = SQLModel.metadata

