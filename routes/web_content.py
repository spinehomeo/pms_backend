# routes/web_content.py
from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from sqlmodel import Session, select
from api.deps import SessionDep, CurrentUser
from models.web_content_model import (
    AboutDoctor,
    Qualification,
    Specialization,
    HeroSection,
    Credential,
    ServicesAndTreatments,
    Service,
    PatientSuccessStories,
    Testimonial,
    ContactInformation,
)
from models.web_content_model import (
    AboutDoctorCreate,
    AboutDoctorUpdate,
    AboutDoctorResponse,
    HeroSectionCreate,
    HeroSectionUpdate,
    HeroSectionResponse,
    ServicesAndTreatmentsCreate,
    ServicesAndTreatmentsUpdate,
    ServicesAndTreatmentsResponse,
    PatientSuccessStoriesCreate,
    PatientSuccessStoriesUpdate,
    PatientSuccessStoriesResponse,
    ContactInformationCreate,
    ContactInformationUpdate,
    ContactInformationResponse,
)

router = APIRouter(prefix="/web-content")


# ==================== ABOUT DOCTOR ENDPOINTS ====================

@router.post(
    "/about-doctor",
    response_model=AboutDoctorResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["📄 Web Content Management - 👨‍⚕️ About Doctor"],
    summary="Create About Doctor Section",
    description="Create a new About Doctor section with qualifications and specializations. Doctor and Admin only."
)
def create_about_doctor(
    about_doctor_data: AboutDoctorCreate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Create About Doctor section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    # Create main about doctor record
    about_doctor = AboutDoctor(
        title=about_doctor_data.title,
        experience_title=about_doctor_data.experience_title,
        experience_description=about_doctor_data.experience_description
    )
    session.add(about_doctor)
    session.commit()
    session.refresh(about_doctor)
    
    # Add qualifications
    for qual_data in about_doctor_data.qualifications:
        qualification = Qualification(
            about_doctor_id=about_doctor.id,
            qualification_text=qual_data.qualification_text,
            order=qual_data.order
        )
        session.add(qualification)
    
    # Add specializations
    for spec_data in about_doctor_data.specializations:
        specialization = Specialization(
            about_doctor_id=about_doctor.id,
            specialization_text=spec_data.specialization_text,
            order=spec_data.order
        )
        session.add(specialization)
    
    session.commit()
    session.refresh(about_doctor)
    
    return about_doctor


@router.get(
    "/about-doctor/{about_doctor_id}",
    response_model=AboutDoctorResponse,
    tags=["📄 Web Content Management - 👨‍⚕️ About Doctor"],
    summary="Get About Doctor Section",
    description="Retrieve About Doctor section by ID. Doctor and Admin only."
)
def get_about_doctor(
    about_doctor_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get About Doctor section by ID - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    about_doctor = session.get(AboutDoctor, about_doctor_id)
    if not about_doctor:
        raise HTTPException(status_code=404, detail="About Doctor section not found")
    return about_doctor


@router.get(
    "/about-doctor",
    response_model=List[AboutDoctorResponse],
    tags=["📄 Web Content Management - 👨‍⚕️ About Doctor"],
    summary="List All About Doctor Sections",
    description="Retrieve all About Doctor sections. Doctor and Admin only."
)
def get_all_about_doctor(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get all About Doctor sections - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    statement = select(AboutDoctor)
    about_doctors = session.exec(statement).all()
    return about_doctors


@router.put(
    "/about-doctor/{about_doctor_id}",
    response_model=AboutDoctorResponse,
    tags=["📄 Web Content Management - 👨‍⚕️ About Doctor"],
    summary="Update About Doctor Section",
    description="Update About Doctor section with new qualifications and specializations. Doctor and Admin only."
)
def update_about_doctor(
    about_doctor_id: int,
    about_doctor_data: AboutDoctorUpdate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Update About Doctor section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    about_doctor = session.get(AboutDoctor, about_doctor_id)
    if not about_doctor:
        raise HTTPException(status_code=404, detail="About Doctor section not found")
    
    # Update main fields
    if about_doctor_data.title is not None:
        about_doctor.title = about_doctor_data.title
    if about_doctor_data.experience_title is not None:
        about_doctor.experience_title = about_doctor_data.experience_title
    if about_doctor_data.experience_description is not None:
        about_doctor.experience_description = about_doctor_data.experience_description
    
    about_doctor.updated_at = datetime.utcnow()
    
    # Update qualifications if provided
    if about_doctor_data.qualifications is not None:
        # Delete existing qualifications
        for qual in about_doctor.qualifications:
            session.delete(qual)
        
        # Add new qualifications
        for qual_data in about_doctor_data.qualifications:
            qualification = Qualification(
                about_doctor_id=about_doctor.id,
                qualification_text=qual_data.qualification_text,
                order=qual_data.order
            )
            session.add(qualification)
    
    # Update specializations if provided
    if about_doctor_data.specializations is not None:
        # Delete existing specializations
        for spec in about_doctor.specializations:
            session.delete(spec)
        
        # Add new specializations
        for spec_data in about_doctor_data.specializations:
            specialization = Specialization(
                about_doctor_id=about_doctor.id,
                specialization_text=spec_data.specialization_text,
                order=spec_data.order
            )
            session.add(specialization)
    
    session.commit()
    session.refresh(about_doctor)
    
    return about_doctor


@router.delete(
    "/about-doctor/{about_doctor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["📄 Web Content Management - 👨‍⚕️ About Doctor"],
    summary="Delete About Doctor Section",
    description="Delete About Doctor section and all related qualifications/specializations. Doctor and Admin only."
)
def delete_about_doctor(
    about_doctor_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> None:
    """Delete About Doctor section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    about_doctor = session.get(AboutDoctor, about_doctor_id)
    if not about_doctor:
        raise HTTPException(status_code=404, detail="About Doctor section not found")
    
    session.delete(about_doctor)
    session.commit()
    
    return None


@router.get(
    "/about-doctor-public/{about_doctor_id}",
    response_model=AboutDoctorResponse,
    tags=["🌍 Public Web Content - 👨‍⚕️ About Doctor"],
    summary="Get About Doctor Section (Public)",
    description="Retrieve About Doctor section by ID without authentication. Public endpoint for website display."
)
def get_about_doctor_public(
    about_doctor_id: int,
    session: SessionDep
) -> Any:
    """Get About Doctor section by ID - PUBLIC (no authentication required)"""
    about_doctor = session.get(AboutDoctor, about_doctor_id)
    if not about_doctor:
        raise HTTPException(status_code=404, detail="About Doctor section not found")
    return about_doctor


@router.get(
    "/about-doctor-public",
    response_model=List[AboutDoctorResponse],
    tags=["🌍 Public Web Content - 👨‍⚕️ About Doctor"],
    summary="List All About Doctor Sections (Public)",
    description="Retrieve all About Doctor sections without authentication. Public endpoint for website display."
)
def get_all_about_doctor_public(
    session: SessionDep
) -> Any:
    """Get all About Doctor sections - PUBLIC (no authentication required)"""
    statement = select(AboutDoctor)
    about_doctors = session.exec(statement).all()
    return about_doctors


# ==================== HERO SECTION ENDPOINTS ====================

@router.post(
    "/hero-section",
    response_model=HeroSectionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["📄 Web Content Management - 🎯 Hero Section"],
    summary="Create Hero Section",
    description="Create a new Hero Section with title, subtitle, description and credentials. Doctor and Admin only."
)
def create_hero_section(
    hero_data: HeroSectionCreate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Create Hero Section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    hero_section = HeroSection(
        title=hero_data.title,
        subtitle=hero_data.subtitle,
        description=hero_data.description
    )
    session.add(hero_section)
    session.commit()
    session.refresh(hero_section)
    
    # Add credentials
    for cred_data in hero_data.credentials:
        credential = Credential(
            hero_section_id=hero_section.id,
            label=cred_data.label,
            value=cred_data.value,
            order=cred_data.order
        )
        session.add(credential)
    
    session.commit()
    session.refresh(hero_section)
    
    return hero_section


@router.get(
    "/hero-section/{hero_id}",
    response_model=HeroSectionResponse,
    tags=["📄 Web Content Management - 🎯 Hero Section"],
    summary="Get Hero Section",
    description="Retrieve Hero Section by ID with all credentials. Doctor and Admin only."
)
def get_hero_section(
    hero_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get Hero Section by ID - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    hero_section = session.get(HeroSection, hero_id)
    if not hero_section:
        raise HTTPException(status_code=404, detail="Hero Section not found")
    return hero_section


@router.get(
    "/hero-section",
    response_model=List[HeroSectionResponse],
    tags=["📄 Web Content Management - 🎯 Hero Section"],
    summary="List All Hero Sections",
    description="Retrieve all Hero Sections. Doctor and Admin only."
)
def get_all_hero_sections(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get all Hero Sections - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    statement = select(HeroSection)
    hero_sections = session.exec(statement).all()
    return hero_sections


@router.put(
    "/hero-section/{hero_id}",
    response_model=HeroSectionResponse,
    tags=["📄 Web Content Management - 🎯 Hero Section"],
    summary="Update Hero Section",
    description="Update Hero Section with new content and credentials. Doctor and Admin only."
)
def update_hero_section(
    hero_id: int,
    hero_data: HeroSectionUpdate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Update Hero Section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    hero_section = session.get(HeroSection, hero_id)
    if not hero_section:
        raise HTTPException(status_code=404, detail="Hero Section not found")
    
    # Update main fields
    if hero_data.title is not None:
        hero_section.title = hero_data.title
    if hero_data.subtitle is not None:
        hero_section.subtitle = hero_data.subtitle
    if hero_data.description is not None:
        hero_section.description = hero_data.description
    
    hero_section.updated_at = datetime.utcnow()
    
    # Update credentials if provided
    if hero_data.credentials is not None:
        # Delete existing credentials
        for cred in hero_section.credentials:
            session.delete(cred)
        
        # Add new credentials
        for cred_data in hero_data.credentials:
            credential = Credential(
                hero_section_id=hero_section.id,
                label=cred_data.label,
                value=cred_data.value,
                order=cred_data.order
            )
            session.add(credential)
    
    session.commit()
    session.refresh(hero_section)
    
    return hero_section


@router.delete(
    "/hero-section/{hero_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["📄 Web Content Management - 🎯 Hero Section"],
    summary="Delete Hero Section",
    description="Delete Hero Section and all associated credentials. Doctor and Admin only."
)
def delete_hero_section(
    hero_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> None:
    """Delete Hero Section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    hero_section = session.get(HeroSection, hero_id)
    if not hero_section:
        raise HTTPException(status_code=404, detail="Hero Section not found")
    
    session.delete(hero_section)
    session.commit()
    
    return None


@router.get(
    "/hero-section-public/{hero_id}",
    response_model=HeroSectionResponse,
    tags=["🌍 Public Web Content - 🎯 Hero Section"],
    summary="Get Hero Section (Public)",
    description="Retrieve Hero Section by ID without authentication. Public endpoint for website display."
)
def get_hero_section_public(
    hero_id: int,
    session: SessionDep
) -> Any:
    """Get Hero Section by ID - PUBLIC (no authentication required)"""
    hero_section = session.get(HeroSection, hero_id)
    if not hero_section:
        raise HTTPException(status_code=404, detail="Hero Section not found")
    return hero_section


@router.get(
    "/hero-section-public",
    response_model=List[HeroSectionResponse],
    tags=["🌍 Public Web Content - 🎯 Hero Section"],
    summary="List All Hero Sections (Public)",
    description="Retrieve all Hero Sections without authentication. Public endpoint for website display."
)
def get_all_hero_sections_public(
    session: SessionDep
) -> Any:
    """Get all Hero Sections - PUBLIC (no authentication required)"""
    statement = select(HeroSection)
    hero_sections = session.exec(statement).all()
    return hero_sections


# ==================== SERVICES & TREATMENTS ENDPOINTS ====================

@router.post(
    "/services",
    response_model=ServicesAndTreatmentsResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["📄 Web Content Management - 🏥 Services & Treatments"],
    summary="Create Services & Treatments Section",
    description="Create a new Services & Treatments section with multiple service items. Doctor and Admin only."
)
def create_services_section(
    services_data: ServicesAndTreatmentsCreate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Create Services & Treatments section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    services_section = ServicesAndTreatments(title=services_data.title)
    session.add(services_section)
    session.commit()
    session.refresh(services_section)
    
    # Add services
    for service_data in services_data.services:
        service = Service(
            services_section_id=services_section.id,
            icon=service_data.icon,
            image_url=service_data.image_url,
            title=service_data.title,
            description=service_data.description,
            order=service_data.order
        )
        session.add(service)
    
    session.commit()
    session.refresh(services_section)
    
    return services_section


@router.get(
    "/services/{services_id}",
    response_model=ServicesAndTreatmentsResponse,
    tags=["📄 Web Content Management - 🏥 Services & Treatments"],
    summary="Get Services & Treatments Section",
    description="Retrieve Services & Treatments section by ID with all services. Doctor and Admin only."
)
def get_services_section(
    services_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get Services & Treatments section by ID - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    services_section = session.get(ServicesAndTreatments, services_id)
    if not services_section:
        raise HTTPException(status_code=404, detail="Services section not found")
    return services_section


@router.get(
    "/services",
    response_model=List[ServicesAndTreatmentsResponse],
    tags=["📄 Web Content Management - 🏥 Services & Treatments"],
    summary="List All Services & Treatments Sections",
    description="Retrieve all Services & Treatments sections. Doctor and Admin only."
)
def get_all_services_sections(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get all Services & Treatments sections - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    statement = select(ServicesAndTreatments)
    services_sections = session.exec(statement).all()
    return services_sections


@router.put(
    "/services/{services_id}",
    response_model=ServicesAndTreatmentsResponse,
    tags=["📄 Web Content Management - 🏥 Services & Treatments"],
    summary="Update Services & Treatments Section",
    description="Update Services & Treatments section with new services. Doctor and Admin only."
)
def update_services_section(
    services_id: int,
    services_data: ServicesAndTreatmentsUpdate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Update Services & Treatments section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    services_section = session.get(ServicesAndTreatments, services_id)
    if not services_section:
        raise HTTPException(status_code=404, detail="Services section not found")
    
    # Update title
    if services_data.title is not None:
        services_section.title = services_data.title
    
    services_section.updated_at = datetime.utcnow()
    
    # Update services if provided
    if services_data.services is not None:
        # Delete existing services
        for service in services_section.services:
            session.delete(service)
        
        # Add new services
        for service_data in services_data.services:
            service = Service(
                services_section_id=services_section.id,
                icon=service_data.icon,
                image_url=service_data.image_url,
                title=service_data.title,
                description=service_data.description,
                order=service_data.order
            )
            session.add(service)
    
    session.commit()
    session.refresh(services_section)
    
    return services_section


@router.delete(
    "/services/{services_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["📄 Web Content Management - 🏥 Services & Treatments"],
    summary="Delete Services & Treatments Section",
    description="Delete Services & Treatments section and all associated services. Doctor and Admin only."
)
def delete_services_section(
    services_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> None:
    """Delete Services & Treatments section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    services_section = session.get(ServicesAndTreatments, services_id)
    if not services_section:
        raise HTTPException(status_code=404, detail="Services section not found")
    
    session.delete(services_section)
    session.commit()
    
    return None


@router.get(
    "/services-public/{services_id}",
    response_model=ServicesAndTreatmentsResponse,
    tags=["🌍 Public Web Content - 🏥 Services & Treatments"],
    summary="Get Services & Treatments Section (Public)",
    description="Retrieve Services & Treatments section by ID without authentication. Public endpoint for website display."
)
def get_services_section_public(
    services_id: int,
    session: SessionDep
) -> Any:
    """Get Services & Treatments section by ID - PUBLIC (no authentication required)"""
    services_section = session.get(ServicesAndTreatments, services_id)
    if not services_section:
        raise HTTPException(status_code=404, detail="Services section not found")
    return services_section


@router.get(
    "/services-public",
    response_model=List[ServicesAndTreatmentsResponse],
    tags=["🌍 Public Web Content - 🏥 Services & Treatments"],
    summary="List All Services & Treatments Sections (Public)",
    description="Retrieve all Services & Treatments sections without authentication. Public endpoint for website display."
)
def get_all_services_sections_public(
    session: SessionDep
) -> Any:
    """Get all Services & Treatments sections - PUBLIC (no authentication required)"""
    statement = select(ServicesAndTreatments)
    services_sections = session.exec(statement).all()
    return services_sections


# ==================== PATIENT SUCCESS STORIES ENDPOINTS ====================

@router.post(
    "/testimonials",
    response_model=PatientSuccessStoriesResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["📄 Web Content Management - ⭐ Testimonials"],
    summary="Create Patient Success Stories Section",
    description="Create a new Patient Success Stories section with testimonials. Doctor and Admin only."
)
def create_testimonials_section(
    testimonials_data: PatientSuccessStoriesCreate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Create Patient Success Stories section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    stories_section = PatientSuccessStories(title=testimonials_data.title)
    session.add(stories_section)
    session.commit()
    session.refresh(stories_section)
    
    # Add testimonials
    for testimonial_data in testimonials_data.testimonials:
        testimonial = Testimonial(
            stories_section_id=stories_section.id,
            name=testimonial_data.name,
            city=testimonial_data.city,
            rating=testimonial_data.rating,
            message=testimonial_data.message,
            order=testimonial_data.order,
            is_approved=testimonial_data.is_approved
        )
        session.add(testimonial)
    
    session.commit()
    session.refresh(stories_section)
    
    return stories_section


@router.get(
    "/testimonials/{testimonials_id}",
    response_model=PatientSuccessStoriesResponse,
    tags=["📄 Web Content Management - ⭐ Testimonials"],
    summary="Get Patient Success Stories Section",
    description="Retrieve Patient Success Stories section by ID with all testimonials. Doctor and Admin only."
)
def get_testimonials_section(
    testimonials_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get Patient Success Stories section by ID - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    stories_section = session.get(PatientSuccessStories, testimonials_id)
    if not stories_section:
        raise HTTPException(status_code=404, detail="Testimonials section not found")
    return stories_section


@router.get(
    "/testimonials",
    response_model=List[PatientSuccessStoriesResponse],
    tags=["📄 Web Content Management - ⭐ Testimonials"],
    summary="List All Patient Success Stories Sections",
    description="Retrieve all Patient Success Stories sections. Doctor and Admin only."
)
def get_all_testimonials_sections(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get all Patient Success Stories sections - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    statement = select(PatientSuccessStories)
    stories_sections = session.exec(statement).all()
    return stories_sections


@router.put(
    "/testimonials/{testimonials_id}",
    response_model=PatientSuccessStoriesResponse,
    tags=["📄 Web Content Management - ⭐ Testimonials"],
    summary="Update Patient Success Stories Section",
    description="Update Patient Success Stories section with new testimonials. Doctor and Admin only."
)
def update_testimonials_section(
    testimonials_id: int,
    testimonials_data: PatientSuccessStoriesUpdate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Update Patient Success Stories section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    stories_section = session.get(PatientSuccessStories, testimonials_id)
    if not stories_section:
        raise HTTPException(status_code=404, detail="Testimonials section not found")
    
    # Update title
    if testimonials_data.title is not None:
        stories_section.title = testimonials_data.title
    
    stories_section.updated_at = datetime.utcnow()
    
    # Update testimonials if provided
    if testimonials_data.testimonials is not None:
        # Delete existing testimonials
        for testimonial in stories_section.testimonials:
            session.delete(testimonial)
        
        # Add new testimonials
        for testimonial_data in testimonials_data.testimonials:
            testimonial = Testimonial(
                stories_section_id=stories_section.id,
                name=testimonial_data.name,
                city=testimonial_data.city,
                rating=testimonial_data.rating,
                message=testimonial_data.message,
                order=testimonial_data.order,
                is_approved=testimonial_data.is_approved
            )
            session.add(testimonial)
    
    session.commit()
    session.refresh(stories_section)
    
    return stories_section


@router.delete(
    "/testimonials/{testimonials_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["📄 Web Content Management - ⭐ Testimonials"],
    summary="Delete Patient Success Stories Section",
    description="Delete Patient Success Stories section and all associated testimonials. Doctor and Admin only."
)
def delete_testimonials_section(
    testimonials_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> None:
    """Delete Patient Success Stories section - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    stories_section = session.get(PatientSuccessStories, testimonials_id)
    if not stories_section:
        raise HTTPException(status_code=404, detail="Testimonials section not found")
    
    session.delete(stories_section)
    session.commit()
    
    return None


@router.get(
    "/testimonials-public/{testimonials_id}",
    response_model=PatientSuccessStoriesResponse,
    tags=["🌍 Public Web Content - ⭐ Testimonials"],
    summary="Get Patient Success Stories Section (Public)",
    description="Retrieve Patient Success Stories section by ID without authentication. Public endpoint for website display."
)
def get_testimonials_section_public(
    testimonials_id: int,
    session: SessionDep
) -> Any:
    """Get Patient Success Stories section by ID - PUBLIC (no authentication required)"""
    stories_section = session.get(PatientSuccessStories, testimonials_id)
    if not stories_section:
        raise HTTPException(status_code=404, detail="Testimonials section not found")
    return stories_section


@router.get(
    "/testimonials-public",
    response_model=List[PatientSuccessStoriesResponse],
    tags=["🌍 Public Web Content - ⭐ Testimonials"],
    summary="List All Patient Success Stories Sections (Public)",
    description="Retrieve all Patient Success Stories sections without authentication. Public endpoint for website display."
)
def get_all_testimonials_sections_public(
    session: SessionDep
) -> Any:
    """Get all Patient Success Stories sections - PUBLIC (no authentication required)"""
    statement = select(PatientSuccessStories)
    stories_sections = session.exec(statement).all()
    return stories_sections


# ==================== CONTACT INFORMATION ENDPOINTS ====================

@router.post(
    "/contact-info",
    response_model=ContactInformationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["📄 Web Content Management - 📞 Contact"],
    summary="Create Contact Information",
    description="Create new Contact Information with phone, address, hours and WhatsApp details. Doctor and Admin only."
)
def create_contact_info(
    contact_data: ContactInformationCreate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Create Contact Information - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    contact_info = ContactInformation(
        title=contact_data.title,
        address=contact_data.address,
        city=contact_data.city,
        phone_primary=contact_data.phone_primary,
        phone_secondary=contact_data.phone_secondary,
        weekdays_hours=contact_data.weekdays_hours,
        saturday_hours=contact_data.saturday_hours,
        sunday_hours=contact_data.sunday_hours,
        whatsapp_number=contact_data.whatsapp_number,
        whatsapp_message=contact_data.whatsapp_message
    )
    session.add(contact_info)
    session.commit()
    session.refresh(contact_info)
    
    return contact_info


@router.get(
    "/contact-info/{contact_id}",
    response_model=ContactInformationResponse,
    tags=["📄 Web Content Management - 📞 Contact"],
    summary="Get Contact Information",
    description="Retrieve Contact Information by ID. Doctor and Admin only."
)
def get_contact_info(
    contact_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get Contact Information by ID - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    contact_info = session.get(ContactInformation, contact_id)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Contact Information not found")
    return contact_info


@router.get(
    "/contact-info",
    response_model=List[ContactInformationResponse],
    tags=["📄 Web Content Management - 📞 Contact"],
    summary="List All Contact Information",
    description="Retrieve all Contact Information records. Doctor and Admin only."
)
def get_all_contact_info(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Get all Contact Information records - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can access website content"
        )
    statement = select(ContactInformation)
    contact_infos = session.exec(statement).all()
    return contact_infos


@router.put(
    "/contact-info/{contact_id}",
    response_model=ContactInformationResponse,
    tags=["📄 Web Content Management - 📞 Contact"],
    summary="Update Contact Information",
    description="Update Contact Information with new phone, address, hours and WhatsApp details. Doctor and Admin only."
)
def update_contact_info(
    contact_id: int,
    contact_data: ContactInformationUpdate,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """Update Contact Information - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    contact_info = session.get(ContactInformation, contact_id)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Contact Information not found")
    
    # Update fields
    update_data = contact_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contact_info, key, value)
    
    contact_info.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(contact_info)
    
    return contact_info


@router.delete(
    "/contact-info/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["📄 Web Content Management - 📞 Contact"],
    summary="Delete Contact Information",
    description="Delete Contact Information record. Doctor and Admin only."
)
def delete_contact_info(
    contact_id: int,
    session: SessionDep,
    current_user: CurrentUser
) -> None:
    """Delete Contact Information - DOCTOR and ADMIN only"""
    if not (current_user.is_doctor or current_user.is_superuser):
        raise HTTPException(
            status_code=403,
            detail="Only doctors and admins can manage website content"
        )
    contact_info = session.get(ContactInformation, contact_id)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Contact Information not found")
    
    session.delete(contact_info)
    session.commit()
    
    return None


@router.get(
    "/contact-info-public/{contact_id}",
    response_model=ContactInformationResponse,
    tags=["🌍 Public Web Content - 📞 Contact"],
    summary="Get Contact Information (Public)",
    description="Retrieve Contact Information by ID without authentication. Public endpoint for website display."
)
def get_contact_info_public(
    contact_id: int,
    session: SessionDep
) -> Any:
    """Get Contact Information by ID - PUBLIC (no authentication required)"""
    contact_info = session.get(ContactInformation, contact_id)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Contact Information not found")
    return contact_info


@router.get(
    "/contact-info-public",
    response_model=List[ContactInformationResponse],
    tags=["🌍 Public Web Content - 📞 Contact"],
    summary="List All Contact Information (Public)",
    description="Retrieve all Contact Information records without authentication. Public endpoint for website display."
)
def get_all_contact_info_public(
    session: SessionDep
) -> Any:
    """Get all Contact Information records - PUBLIC (no authentication required)"""
    statement = select(ContactInformation)
    contact_infos = session.exec(statement).all()
    return contact_infos

