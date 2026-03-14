# models/prescriptions_model.py - WITH QUICK-ADD SUPPORT + AUTO FOLLOW-UP SCHEDULING
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


# ========== DATABASE MODELS (CRUD) ==========
class PrescriptionBase(SQLModel):
    """Base prescription model"""
    prescription_type: str = Field(max_length=100)
    dosage: Optional[str] = Field(default=None, max_length=200)
    prescription_duration: str = Field(max_length=100)          # Human-readable string e.g. "30 days"
    duration_days: Optional[int] = Field(default=None, ge=1)    # NEW: integer version for auto date calculation
    instructions: Optional[str] = Field(default=None)
    follow_up_advice: Optional[str] = Field(default=None)       # kept for backward-compat; superseded by follow_up_schedule.notes
    dietary_restrictions: Optional[str] = Field(default=None)
    avoidance: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class Prescription(PrescriptionBase, table=True):
    """DATABASE MODEL for prescriptions - USED FOR CRUD"""
    __tablename__ = "prescription"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="patient_case.id",
        nullable=False,
        index=True
    )
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    prescription_date: date = Field(default_factory=date.today)
    prescription_number: str = Field(max_length=50, unique=True, index=True)
    status: str = Field(default="open", max_length=50)  # From PrescriptionStatus enum: open, completed, cancelled
    
    # Relationships
    case: "PatientCase" = Relationship(back_populates="prescriptions")
    doctor: "User" = Relationship(back_populates="prescriptions")
    medicines: List["PrescriptionMedicine"] = Relationship(back_populates="prescription")
    follow_ups: List["FollowUp"] = Relationship(back_populates="prescription")


class PrescriptionMedicine(SQLModel, table=True):
    """DATABASE MODEL for prescription-medicine mapping"""
    __tablename__ = "prescription_medicine"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prescription_id: uuid.UUID = Field(
        foreign_key="prescription.id",
        nullable=False,
        index=True
    )
    medicine_id: uuid.UUID = Field(
        foreign_key="medicine.id",
        nullable=False,
        index=True
    )
    quantity_prescribed: Optional[str] = Field(default=None, max_length=100)
    frequency: Optional[str] = Field(default=None, max_length=50)  # From RepetitionInterval enum: OD, BD, TDS, etc
    
    # Relationships
    prescription: Prescription = Relationship(back_populates="medicines")
    medicine: "Medicine" = Relationship(back_populates="prescriptions")


# ========== REQUEST MODELS (API Input) ==========
class QuickAddMedicineData(SQLModel):
    """Data for quick-adding a new medicine during prescription"""
    name: str = Field(max_length=255)
    potency: str = Field(max_length=50)
    potency_scale: str = Field(default="C")  # C, X, Q
    form: str = Field(default="Globules")
    manufacturer: Optional[str] = None
    description: Optional[str] = None


class PrescriptionMedicineCreate(SQLModel):
    """
    API INPUT MODEL for prescription medicines.
    
    Supports TWO modes:
    1. Use existing medicine: Provide medicine_id
    2. Quick-add new medicine: Provide new_medicine
    """
    # Mode 1: Existing medicine
    medicine_id: Optional[uuid.UUID] = None
    
    # Mode 2: Quick-add new medicine
    new_medicine: Optional[QuickAddMedicineData] = None
    
    # Common fields
    quantity_prescribed: Optional[str] = Field(default=None, max_length=100)
    frequency: Optional[str] = Field(default=None, max_length=50)  # From RepetitionInterval enum
    
    def model_post_init(self, __context):
        """Validate that exactly one of medicine_id or new_medicine is provided"""
        if not self.medicine_id and not self.new_medicine:
            raise ValueError("Either medicine_id or new_medicine must be provided")
        if self.medicine_id and self.new_medicine:
            raise ValueError("Provide either medicine_id OR new_medicine, not both")


# NEW: Embedded follow-up scheduling block inside PrescriptionCreate
class FollowUpSchedule(SQLModel):
    """
    Optional follow-up scheduling block embedded in PrescriptionCreate.

    Priority order for determining the follow-up date:
      1. follow_up_date  — explicit date chosen by the doctor (highest priority)
      2. auto_calculate=True — backend derives date as: prescription_date + duration_days
      3. Neither set   — backend falls back to prescription_date + 30 days

    notes: replaces the top-level follow_up_advice field for scheduled follow-ups.
    """
    follow_up_date: Optional[date] = None
    interval_days: Optional[int] = Field(default=None, ge=7)   # explicit override; if omitted, calculated automatically
    auto_calculate: bool = False                                 # derive date from duration_days on the prescription
    notes: Optional[str] = None                                 # stored as follow-up plan / advice


class PrescriptionCreate(PrescriptionBase):
    """API INPUT MODEL for creating prescriptions"""
    case_id: uuid.UUID
    medicines: List[PrescriptionMedicineCreate] = []
    status: Optional[str] = Field(default="open", max_length=50)  # From PrescriptionStatus enum

    # NEW: optional inline follow-up scheduling; omit to skip auto-creation
    follow_up_schedule: Optional[FollowUpSchedule] = None


class PrescriptionUpdate(SQLModel):
    """API INPUT MODEL for updating prescriptions"""
    dosage: Optional[str] = None
    prescription_duration: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1)   # NEW: allow updating the integer duration too
    instructions: Optional[str] = None
    follow_up_advice: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    avoidance: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)  # From PrescriptionStatus enum
    medicines: Optional[List[PrescriptionMedicineCreate]] = None


# ========== RESPONSE MODELS (API Output) ==========
class MedicineBasicInfo(SQLModel):
    """Basic medicine info for prescription response"""
    id: uuid.UUID
    name: str
    potency: str
    form: str


class PrescriptionMedicinePublic(SQLModel):
    """API OUTPUT MODEL for prescription medicines"""
    id: uuid.UUID
    medicine_id: uuid.UUID
    quantity_prescribed: Optional[str] = None
    frequency: Optional[str] = None  # From RepetitionInterval enum
    medicine: MedicineBasicInfo


class PrescriptionPublic(PrescriptionBase):
    """API OUTPUT MODEL for single prescription"""
    id: uuid.UUID
    case_id: uuid.UUID
    doctor_id: uuid.UUID
    prescription_date: date
    prescription_number: str
    status: str  # From PrescriptionStatus enum
    medicines: List[PrescriptionMedicinePublic] = []
    patient_name: Optional[str] = None
    case_number: Optional[str] = None


class PrescriptionsPublic(SQLModel):
    """API OUTPUT MODEL for list of prescriptions"""
    data: List[PrescriptionPublic]
    count: int


# NEW: Response model for POST /prescriptions/ when follow_up_schedule is provided
class PrescriptionCreateResponse(SQLModel):
    """
    API OUTPUT MODEL for prescription creation.

    Always contains the full prescription.
    When follow_up_schedule was provided, follow_up_scheduled=True and
    follow_up_id / follow_up_date are populated.
    Call GET /followups/{follow_up_id} for the full follow-up record.
    """
    prescription: PrescriptionPublic
    follow_up_scheduled: bool = False
    follow_up_id: Optional[uuid.UUID] = None
    follow_up_date: Optional[date] = None


class PrintPrescriptionResponse(SQLModel):
    """API OUTPUT MODEL for printing prescriptions"""
    prescription: PrescriptionPublic
    patient: dict
    doctor: dict
    print_date: str