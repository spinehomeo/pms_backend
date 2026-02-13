# # (pms-backend) F:\2_PROJECTS\B_PMS\pms_backend>python.exe -m utils.initial_data
# # INFO:__main__:Creating initial data
# # INFO:__main__:Initial data created
import logging
from datetime import date
from sqlmodel import Session, select

from core.db import engine
from core.security import get_password_hash
from models.medicines_model import Medicine, FormEnum, ScaleEnum
from models.patients_model import PatientGender
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
            "potency_scale": ScaleEnum.C,
            "form": FormEnum.GLOBULES,
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
            "potency_scale": ScaleEnum.C,
            "form": FormEnum.GLOBULES,
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
            "potency_scale": ScaleEnum.C,
            "form": FormEnum.GLOBULES,
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
            "potency_scale": ScaleEnum.C,
            "form": FormEnum.GLOBULES,
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
            "potency_scale": ScaleEnum.C,
            "form": FormEnum.GLOBULES,
            "quantity": 90.0,
            "unit": "bottle",
            "batch_number": "SULPH200-001",
            "expiry_date": date(2025, 8, 31),
            "manufacturer": "Standard Homeopathic",
            "storage_location": "Cabinet C, Shelf 1",
            "low_stock_threshold": 20.0
        }
    ]
    
    from models.medicines_model import DoctorMedicineStock
    
    for stock_data in initial_stock:
        if stock_data["medicine_id"]:
            stock = DoctorMedicineStock(
                doctor_id=doctor_id,
                **stock_data
            )
            session.add(stock)
    
    session.commit()
    logger.info(f"Created initial medicine stock for doctor {doctor_id}")


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
        
        # Create initial stock for the doctor
        if doctor_id:
            create_initial_stock(session, doctor_id)
        
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