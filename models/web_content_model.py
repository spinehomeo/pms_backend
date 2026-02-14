from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel
from pydantic import BaseModel


# ==================== DATABASE MODELS ====================

# About Doctor Section
class AboutDoctor(SQLModel, table=True):
    """Main table for About Doctor section"""
    __tablename__ = "about_doctor"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    experience_title: str = Field(max_length=200)
    experience_description: str = Field(max_length=5000)  # Can store JSON array as string
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    qualifications: List["Qualification"] = Relationship(back_populates="about_doctor", cascade_delete=True)
    specializations: List["Specialization"] = Relationship(back_populates="about_doctor", cascade_delete=True)


class Qualification(SQLModel, table=True):
    """Qualifications of the doctor"""
    __tablename__ = "qualifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    about_doctor_id: int = Field(foreign_key="about_doctor.id", ondelete="CASCADE")
    qualification_text: str = Field(max_length=500)
    order: int = Field(default=0)  # For maintaining order
    
    # Relationships
    about_doctor: AboutDoctor = Relationship(back_populates="qualifications")


class Specialization(SQLModel, table=True):
    """Doctor's specializations"""
    __tablename__ = "specializations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    about_doctor_id: int = Field(foreign_key="about_doctor.id", ondelete="CASCADE")
    specialization_text: str = Field(max_length=500)
    order: int = Field(default=0)
    
    # Relationships
    about_doctor: AboutDoctor = Relationship(back_populates="specializations")


# Hero Section
class HeroSection(SQLModel, table=True):
    """Hero section of the website"""
    __tablename__ = "hero_section"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    subtitle: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    credentials: List["Credential"] = Relationship(back_populates="hero_section", cascade_delete=True)


class Credential(SQLModel, table=True):
    """Credentials displayed in hero section"""
    __tablename__ = "credentials"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hero_section_id: int = Field(foreign_key="hero_section.id", ondelete="CASCADE")
    label: str = Field(max_length=200)
    value: str = Field(max_length=200)
    order: int = Field(default=0)
    
    # Relationships
    hero_section: HeroSection = Relationship(back_populates="credentials")


# Services and Treatments
class ServicesAndTreatments(SQLModel, table=True):
    """Main table for services section"""
    __tablename__ = "services_and_treatments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    services: List["Service"] = Relationship(back_populates="services_section", cascade_delete=True)


class Service(SQLModel, table=True):
    """Individual services offered"""
    __tablename__ = "services"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    services_section_id: int = Field(foreign_key="services_and_treatments.id", ondelete="CASCADE")
    icon: str = Field(max_length=100)
    image_url: str = Field(max_length=500)
    title: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    order: int = Field(default=0)
    
    # Relationships
    services_section: ServicesAndTreatments = Relationship(back_populates="services")


# Patient Success Stories
class PatientSuccessStories(SQLModel, table=True):
    """Main table for testimonials section"""
    __tablename__ = "patient_success_stories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    testimonials: List["Testimonial"] = Relationship(back_populates="stories_section", cascade_delete=True)


class Testimonial(SQLModel, table=True):
    """Patient testimonials"""
    __tablename__ = "testimonials"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    stories_section_id: int = Field(foreign_key="patient_success_stories.id", ondelete="CASCADE")
    name: str = Field(max_length=200)
    city: str = Field(max_length=200)
    rating: int = Field(ge=1, le=5)
    message: str = Field(max_length=2000)
    order: int = Field(default=0)
    is_approved: bool = Field(default=True)  # For moderation
    
    # Relationships
    stories_section: PatientSuccessStories = Relationship(back_populates="testimonials")


# Contact Information
class ContactInformation(SQLModel, table=True):
    """Contact information table"""
    __tablename__ = "contact_information"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    address: str = Field(max_length=500)
    city: str = Field(max_length=200)
    phone_primary: str = Field(max_length=50)
    phone_secondary: Optional[str] = Field(default=None, max_length=50)
    weekdays_hours: str = Field(max_length=200)
    saturday_hours: str = Field(max_length=200)
    sunday_hours: str = Field(max_length=200)
    whatsapp_number: str = Field(max_length=50)
    whatsapp_message: str = Field(max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== PYDANTIC SCHEMAS ====================

# About Doctor Schemas
class QualificationCreate(BaseModel):
    qualification_text: str
    order: int = 0


class SpecializationCreate(BaseModel):
    specialization_text: str
    order: int = 0


class AboutDoctorCreate(BaseModel):
    title: str
    experience_title: str
    experience_description: str
    qualifications: List[QualificationCreate]
    specializations: List[SpecializationCreate]


class AboutDoctorUpdate(BaseModel):
    title: Optional[str] = None
    experience_title: Optional[str] = None
    experience_description: Optional[str] = None
    qualifications: Optional[List[QualificationCreate]] = None
    specializations: Optional[List[SpecializationCreate]] = None


class QualificationResponse(BaseModel):
    id: int
    qualification_text: str
    order: int
    
    class Config:
        from_attributes = True


class SpecializationResponse(BaseModel):
    id: int
    specialization_text: str
    order: int
    
    class Config:
        from_attributes = True


class AboutDoctorResponse(BaseModel):
    id: int
    title: str
    experience_title: str
    experience_description: str
    qualifications: List[QualificationResponse]
    specializations: List[SpecializationResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Hero Section Schemas
class CredentialCreate(BaseModel):
    label: str
    value: str
    order: int = 0


class HeroSectionCreate(BaseModel):
    title: str
    subtitle: str
    description: str
    credentials: List[CredentialCreate]


class HeroSectionUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    credentials: Optional[List[CredentialCreate]] = None


class CredentialResponse(BaseModel):
    id: int
    label: str
    value: str
    order: int
    
    class Config:
        from_attributes = True


class HeroSectionResponse(BaseModel):
    id: int
    title: str
    subtitle: str
    description: str
    credentials: List[CredentialResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Services Schemas
class ServiceCreate(BaseModel):
    icon: str
    image_url: str
    title: str
    description: str
    order: int = 0


class ServicesAndTreatmentsCreate(BaseModel):
    title: str
    services: List[ServiceCreate]


class ServicesAndTreatmentsUpdate(BaseModel):
    title: Optional[str] = None
    services: Optional[List[ServiceCreate]] = None


class ServiceResponse(BaseModel):
    id: int
    icon: str
    image_url: str
    title: str
    description: str
    order: int
    
    class Config:
        from_attributes = True


class ServicesAndTreatmentsResponse(BaseModel):
    id: int
    title: str
    services: List[ServiceResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Testimonials Schemas
class TestimonialCreate(BaseModel):
    name: str
    city: str
    rating: int
    message: str
    order: int = 0
    is_approved: bool = True


class PatientSuccessStoriesCreate(BaseModel):
    title: str
    testimonials: List[TestimonialCreate]


class PatientSuccessStoriesUpdate(BaseModel):
    title: Optional[str] = None
    testimonials: Optional[List[TestimonialCreate]] = None


class TestimonialResponse(BaseModel):
    id: int
    name: str
    city: str
    rating: int
    message: str
    order: int
    is_approved: bool
    
    class Config:
        from_attributes = True


class PatientSuccessStoriesResponse(BaseModel):
    id: int
    title: str
    testimonials: List[TestimonialResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Contact Information Schemas
class ContactInformationCreate(BaseModel):
    title: str
    address: str
    city: str
    phone_primary: str
    phone_secondary: Optional[str] = None
    weekdays_hours: str
    saturday_hours: str
    sunday_hours: str
    whatsapp_number: str
    whatsapp_message: str


class ContactInformationUpdate(BaseModel):
    title: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    weekdays_hours: Optional[str] = None
    saturday_hours: Optional[str] = None
    sunday_hours: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_message: Optional[str] = None


class ContactInformationResponse(BaseModel):
    id: int
    title: str
    address: str
    city: str
    phone_primary: str
    phone_secondary: Optional[str]
    weekdays_hours: str
    saturday_hours: str
    sunday_hours: str
    whatsapp_number: str
    whatsapp_message: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

