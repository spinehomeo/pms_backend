# # (pms-backend) F:\2_PROJECTS\B_PMS\pms_backend>python.exe -m utils.initial_data
# # INFO:__main__:Creating initial data
# # INFO:__main__:Initial data created
import logging
from datetime import date
from sqlmodel import Session, select

from core.db import engine
from core.security import get_password_hash
from models.medicines_model import Medicine
from models.users_model import User, UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_superuser(session: Session) -> None:
    """Create initial superuser account"""
    # Check if superuser already exists
    existing_superuser = session.exec(
        select(User).where(User.email == "admin@homoeomed.com")
    ).first()
    
    if existing_superuser:
        logger.info("Superuser already exists")
        return
    
    superuser = User(
        email="admin@homoeomed.com",
        full_name="System Administrator",
        hashed_password=get_password_hash("Admin@123"),  # Change this in production!
        role=UserRole.ADMIN,
        phone="+1234567890",
        specialization="System Administration",
        registration_number="ADMIN001",
        clinic_name="HomoeoMed Headquarters",
        clinic_address="123 Main Street, City, Country",
        consultation_fee=0.0,
        is_active=True,
        is_verified=True,
        is_superuser=True,
        join_date=date.today()
    )
    
    session.add(superuser)
    session.commit()
    logger.info(f"Superuser created: {superuser.email}")


def create_sample_doctor(session: Session) -> None:
    """Create sample doctor account"""
    existing_doctor = session.exec(
        select(User).where(User.email == "doctor@homoeomed.com")
    ).first()
    
    if existing_doctor:
        logger.info("Sample doctor already exists")
        return
    
    doctor = User(
        email="doctor@homoeomed.com",
        full_name="Dr. John Smith",
        hashed_password=get_password_hash("Doctor@123"),
        role=UserRole.DOCTOR,
        phone="+1234567891",
        specialization="Homeopathy",
        registration_number="HOM001",
        clinic_name="Smith Homeopathy Clinic",
        clinic_address="456 Health Street, City, Country",
        consultation_fee=50.0,
        is_active=True,
        is_verified=True,
        is_superuser=False,
        join_date=date.today()
    )
    
    session.add(doctor)
    session.commit()
    logger.info(f"Sample doctor created: {doctor.email}")
    return doctor.id


def create_sample_staff(session: Session) -> None:
    """Create sample staff account"""
    existing_staff = session.exec(
        select(User).where(User.email == "staff@homoeomed.com")
    ).first()
    
    if existing_staff:
        logger.info("Sample staff already exists")
        return
    
    staff = User(
        email="staff@homoeomed.com",
        full_name="Sarah Johnson",
        hashed_password=get_password_hash("Staff@123"),
        role=UserRole.STAFF,
        phone="+1234567892",
        specialization="Clinic Management",
        registration_number="STAFF001",
        clinic_name="Smith Homeopathy Clinic",
        clinic_address="456 Health Street, City, Country",
        consultation_fee=0.0,
        is_active=True,
        is_verified=True,
        is_superuser=False,
        join_date=date.today()
    )
    
    session.add(staff)
    session.commit()
    logger.info(f"Sample staff created: {staff.email}")


def create_common_medicines(session: Session) -> None:
    """Create common homeopathic medicines in master"""
    common_medicines = [
        {
            "name": "Arnica Montana",
            "abbreviation": "Arn",
            "notes": "For trauma, bruises, and shock"
        },
        {
            "name": "Belladonna",
            "abbreviation": "Bell",
            "notes": "For sudden, intense conditions with heat"
        },
        {
            "name": "Nux Vomica",
            "abbreviation": "Nux-v",
            "notes": "For digestive issues and stress"
        },
        {
            "name": "Pulsatilla",
            "abbreviation": "Puls",
            "notes": "For changeable symptoms, gentle disposition"
        },
        {
            "name": "Sulphur",
            "abbreviation": "Sulph",
            "notes": "For skin conditions and heat"
        }
    ]
    
    for medicine_data in common_medicines:
        existing = session.exec(
            select(Medicine).where(Medicine.name == medicine_data["name"])
        ).first()
        
        if not existing:
            medicine = Medicine(**medicine_data)
            session.add(medicine)
    
    session.commit()
    logger.info(f"Created {len(common_medicines)} common medicines")


def create_initial_stock(session: Session, doctor_id: str) -> None:
    """Create initial medicine stock for the doctor"""
    # Get medicine IDs
    medicines = session.exec(select(Medicine)).all()
    medicine_map = {m.name: m.id for m in medicines}
    
    initial_stock = [
        {
            "medicine_id": medicine_map.get("Arnica Montana"),
            "potency": "200",
            "potency_scale": "C",
            "form": "Globules",
            "quantity": 100.0,
            "unit": "bottle",
            "batch_number": "ARN200-001",
            "expiry_date": date(2025, 12, 31),
            "manufacturer": "Standard Homeopathic",
            "storage_location": "Cabinet A, Shelf 1",
            "low_stock_threshold": 20.0
        },
        {
            "medicine_id": medicine_map.get("Belladonna"),
            "potency": "30",
            "potency_scale": "C",
            "form": "Globules",
            "quantity": 150.0,
            "unit": "bottle",
            "batch_number": "BELL30-001",
            "expiry_date": date(2025, 10, 31),
            "manufacturer": "Standard Homeopathic",
            "storage_location": "Cabinet A, Shelf 2",
            "low_stock_threshold": 30.0
        },
        {
            "medicine_id": medicine_map.get("Nux Vomica"),
            "potency": "30",
            "potency_scale": "C",
            "form": "Globules",
            "quantity": 120.0,
            "unit": "bottle",
            "batch_number": "NUX30-001",
            "expiry_date": date(2025, 11, 30),
            "manufacturer": "Standard Homeopathic",
            "storage_location": "Cabinet B, Shelf 1",
            "low_stock_threshold": 25.0
        },
        {
            "medicine_id": medicine_map.get("Pulsatilla"),
            "potency": "200",
            "potency_scale": "C",
            "form": "Globules",
            "quantity": 80.0,
            "unit": "bottle",
            "batch_number": "PULS200-001",
            "expiry_date": date(2025, 9, 30),
            "manufacturer": "Standard Homeopathic",
            "storage_location": "Cabinet B, Shelf 2",
            "low_stock_threshold": 15.0
        },
        {
            "medicine_id": medicine_map.get("Sulphur"),
            "potency": "200",
            "potency_scale": "C",
            "form": "Globules",
            "quantity": 90.0,
            "unit": "bottle",
            "batch_number": "SULPH200-001",
            "expiry_date": date(2025, 8, 31),
            "manufacturer": "Standard Homeopathic",
            "storage_location": "Cabinet C, Shelf 1",
            "low_stock_threshold": 20.0
        }
    ]
    
    # Stock creation not needed with global medicine catalog
    # Doctors now access shared medicine catalog instead
    logger.info(f"Skipping stock initialization - using global medicine catalog for doctor {doctor_id}")


def seed_enum_types(session: Session) -> None:
    """Seed all 10 enum types into the database"""
    from models.enum_option_model import EnumType
    
    ENUM_TYPE_SEEDS = [
        ("RepetitionEnum", "Repetition", "Prescription repetition frequency"),
        ("PrescriptionType", "Prescription Type", "Types of homeopathic prescriptions"),
        ("UserRole", "User Role", "System roles"),
        ("PatientGender", "Patient Gender", "Gender options for patient profile"),
        ("ConsultationType", "Consultation Type", "Types of consultation appointments"),
        ("AppointmentStatus", "Appointment Status", "Lifecycle status of appointments"),
        ("PrescriptionStatus", "Prescription Status", "Lifecycle status of prescriptions"),
        ("FollowupStatus", "Followup Status", "Status of follow-up appointments"),
        ("CaseStatus", "Case Status", "Status of patient cases"),
        ("ScaleEnum", "Scale", "Medicine potency scale"),
        ("FormEnum", "Medicine Form", "Physical form of medicine"),
        ("ManufacturerEnum", "Manufacturer", "Medicine manufacturers"),
        ("DayOfWeek", "Day of Week", "Days for doctor availability"),
        ("ExceptionType", "Exception Type", "Availability exception categories"),
    ]
    
    for key, label, description in ENUM_TYPE_SEEDS:
        existing = session.exec(
            select(EnumType).where(EnumType.key == key)
        ).first()
        
        if not existing:
            enum_type = EnumType(
                key=key,
                label=label,
                description=description,
                is_system=True,
            )
            session.add(enum_type)
            logger.info(f"Created enum type: {key}")
        else:
            logger.info(f"Enum type '{key}' already exists")
    
    session.commit()


def seed_enum_options(session: Session) -> None:
    """Seed all enum options into the database"""
    from models.enum_option_model import EnumOption, EnumType
    
    ENUM_OPTIONS_SEEDS = {
        "RepetitionEnum": [
            ("OD", "Once Daily (OD)"),
            ("BD", "Twice Daily (BD)"),
            ("TDS", "Three Times Daily (TDS)"),
            ("Once Weekly", "Once Weekly"),
            ("Once in 10 Days", "Once in 10 Days"),
            ("Fortnightly", "Fortnightly"),
            ("Monthly", "Monthly"),
        ],
        "PrescriptionType": [
            ("Constitutional", "Constitutional"),
            ("Classical", "Classical"),
            ("Inter Current", "Inter Current"),
            ("Pure Bio Chemic", "Pure Bio Chemic"),
            ("Mother Tincture", "Mother Tincture"),
            ("Patent", "Patent"),
        ],
        "UserRole": [
            ("admin", "Admin"),
            ("doctor", "Doctor"),
            ("staff", "Staff"),
        ],
        "PatientGender": [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("child", "Child"),
        ],
        "ConsultationType": [
            ("first", "First Consultation"),
            ("follow-up", "Follow-up Consultation"),
            ("emergency", "Emergency Consultation"),
            ("review", "Review Consultation"),
        ],
        "AppointmentStatus": [
            ("scheduled", "Scheduled"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
            ("completed", "Completed"),
            ("no-show", "No Show"),
        ],
        "PrescriptionStatus": [
            ("open", "Open"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        "FollowupStatus": [
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
            ("pending", "Pending"),
            ("cancelled", "Cancelled"),
        ],
        "CaseStatus": [
            ("open", "Open"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("archived", "Archived"),
        ],
        "ScaleEnum": [
            ("X", "Decimal (X)"),
            ("C", "Centesimal (C)"),
            ("LM", "LM Potency"),
            ("Q", "Quinquagintamillesimal (Q)"),
            ("M", "Fifty Millesimal (M)"),
            ("CM", "Hundred Millesimal (CM)"),
            ("MM", "Thousand Millesimal (MM)"),
        ],
        "FormEnum": [
            ("Tablet", "Tablet"),
            ("Syrup", "Syrup"),
            ("Capsule", "Capsule"),
            ("Injection", "Injection"),
            ("Drops", "Drops"),
            ("Globules", "Globules"),
            ("Powder", "Powder"),
        ],
        "ManufacturerEnum": [
            ("Manufacturer A", "Manufacturer A"),
            ("Manufacturer B", "Manufacturer B"),
            ("Local", "Local"),
        ],
        "DayOfWeek": [
            ("monday", "Monday"),
            ("tuesday", "Tuesday"),
            ("wednesday", "Wednesday"),
            ("thursday", "Thursday"),
            ("friday", "Friday"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
        ],
        "ExceptionType": [
            ("Holiday", "Holiday"),
            ("Emergency", "Emergency"),
            ("Personal Leave", "Personal Leave"),
        ],
    }
    
    for enum_type_key, options in ENUM_OPTIONS_SEEDS.items():
        # Get the enum type
        enum_type = session.exec(
            select(EnumType).where(EnumType.key == enum_type_key)
        ).first()
        
        if not enum_type:
            logger.warning(f"Enum type '{enum_type_key}' not found, skipping options")
            continue
        
        for i, (value, label) in enumerate(options):
            existing = session.exec(
                select(EnumOption).where(
                    EnumOption.enum_type_id == enum_type.id,
                    EnumOption.value == value
                )
            ).first()
            
            if not existing:
                option = EnumOption(
                    enum_type_id=enum_type.id,
                    enum_type=enum_type_key,
                    value=value,
                    label=label,
                    sort_order=i,
                    is_system=True,
                )
                session.add(option)
                logger.info(f"Created option: {enum_type_key} -> {value}")
            else:
                logger.info(f"Option '{value}' already exists for {enum_type_key}")
    
    session.commit()


def init() -> None:
    """Initialize database with essential data"""
    with Session(engine) as session:
        # Create superuser
        create_superuser(session)
        
        # Create sample doctor
        doctor_id = create_sample_doctor(session)
        
        # Create sample staff
        create_sample_staff(session)
        
        # Create common medicines
        create_common_medicines(session)
        
        # Seed enum types and options
        seed_enum_types(session)
        seed_enum_options(session)
        
        session.commit()


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created successfully")


if __name__ == "__main__":
    main()


# (pms-backend) F:\2_PROJECTS\B_PMS\pms_backend>python.exe -m utils.initial_data
# INFO:__main__:Creating initial data
# INFO:__main__:Superuser created: admin@homoeomed.com
# INFO:__main__:Sample doctor created: doctor@homoeomed.com
# INFO:__main__:Sample staff created: staff@homoeomed.com
# INFO:__main__:Created 5 common medicines
# INFO:__main__:Created initial medicine stock for doctor 1ffd1a39-e9a3-46d3-8cd3-950dab11455e
# INFO:__main__:Initial data created successfully