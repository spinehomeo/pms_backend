# utils/enum_service.py
"""
Core service for managing dynamic enums across all 10 enum types.
Handles validation, filtering by role, and doctor-specific preferences.
"""

from typing import Optional
from uuid import UUID

from sqlmodel import Session, select
from sqlalchemy import and_

from models.enum_option_model import (
    EnumType, EnumOption, DoctorEnumPreference, EnumOptionCreate
)


class EnumService:
    """Reusable service for all enum operations"""
    
    # ========================================================================
    # ENUM TYPE OPERATIONS
    # ========================================================================
    
    @staticmethod
    def get_all_enum_types(session: Session, active_only: bool = True) -> list[EnumType]:
        """Get all registered enum types (admin view)"""
        query = select(EnumType)
        if active_only:
            query = query.where(EnumType.is_active == True)
        return session.exec(query.order_by(EnumType.label)).all()
    
    @staticmethod
    def get_enum_type_by_key(session: Session, key: str) -> Optional[EnumType]:
        """Get a specific enum type by its key"""
        return session.exec(
            select(EnumType).where(EnumType.key == key)
        ).first()
    
    @staticmethod
    def create_enum_type(
        session: Session,
        key: str,
        label: str,
        description: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> EnumType:
        """Create a new enum type"""
        # Check for duplicates
        existing = EnumService.get_enum_type_by_key(session, key)
        if existing:
            raise ValueError(f"Enum type '{key}' already exists")
        
        enum_type = EnumType(
            key=key,
            label=label,
            description=description,
            created_by=created_by,
            is_system=False
        )
        session.add(enum_type)
        session.commit()
        session.refresh(enum_type)
        return enum_type
    
    @staticmethod
    def delete_enum_type(session: Session, enum_type_id: UUID) -> None:
        """Delete an enum type (and cascade delete options)"""
        enum_type = session.get(EnumType, enum_type_id)
        if not enum_type:
            raise ValueError(f"Enum type {enum_type_id} not found")
        
        if enum_type.is_system:
            raise ValueError("Cannot delete a system enum type. Disable it instead.")
        
        # Delete all options for this type
        session.exec(
            select(EnumOption)
            .where(EnumOption.enum_type_id == enum_type_id)
        )
        for opt in session.exec(
            select(EnumOption).where(EnumOption.enum_type_id == enum_type_id)
        ).all():
            session.delete(opt)
        
        session.delete(enum_type)
        session.commit()
    
    # ========================================================================
    # ENUM OPTION OPERATIONS - GLOBAL
    # ========================================================================
    
    @staticmethod
    def get_global_options(
        session: Session,
        enum_type_key: str,
        active_only: bool = True
    ) -> list[EnumOption]:
        """
        Get all active options for an enum type (admin view).
        Returns all global options regardless of doctor preferences.
        """
        query = (
            select(EnumOption)
            .where(EnumOption.enum_type == enum_type_key)
        )
        if active_only:
            query = query.where(EnumOption.is_active == True)
        
        return session.exec(
            query.order_by(EnumOption.sort_order, EnumOption.created_at)
        ).all()
    
    @staticmethod
    def get_option_by_id(session: Session, option_id: UUID) -> Optional[EnumOption]:
        """Get a specific option by ID"""
        return session.get(EnumOption, option_id)
    
    @staticmethod
    def create_enum_option(
        session: Session,
        enum_type_key: str,
        value: str,
        label: str,
        sort_order: int = 0,
        created_by: Optional[UUID] = None,
        is_system: bool = False
    ) -> EnumOption:
        """Create a new enum option"""
        # Verify enum type exists
        enum_type = EnumService.get_enum_type_by_key(session, enum_type_key)
        if not enum_type:
            raise ValueError(f"Enum type '{enum_type_key}' not found")
        
        # Check for duplicates within this type
        existing = session.exec(
            select(EnumOption)
            .where(and_(
                EnumOption.enum_type_id == enum_type.id,
                EnumOption.value == value
            ))
        ).first()
        if existing:
            raise ValueError(f"Option '{value}' already exists for {enum_type_key}")
        
        option = EnumOption(
            enum_type_id=enum_type.id,
            enum_type=enum_type_key,
            value=value,
            label=label,
            sort_order=sort_order,
            created_by=created_by,
            is_system=is_system
        )
        session.add(option)
        session.commit()
        session.refresh(option)
        return option
    
    @staticmethod
    def delete_enum_option(session: Session, option_id: UUID) -> None:
        """Delete an enum option"""
        option = session.get(EnumOption, option_id)
        if not option:
            raise ValueError(f"Option {option_id} not found")
        
        if option.is_system:
            raise ValueError("Cannot delete a system option. Disable it instead.")
        
        # Cascade delete doctor preferences
        session.exec(
            select(DoctorEnumPreference)
            .where(DoctorEnumPreference.enum_option_id == option_id)
        )
        for pref in session.exec(
            select(DoctorEnumPreference).where(DoctorEnumPreference.enum_option_id == option_id)
        ).all():
            session.delete(pref)
        
        session.delete(option)
        session.commit()
    
    # ========================================================================
    # ENUM OPTION OPERATIONS - DOCTOR-FILTERED
    # ========================================================================
    
    @staticmethod
    def get_doctor_options(
        session: Session,
        enum_type_key: str,
        doctor_id: UUID
    ) -> list[EnumOption]:
        """
        Get options visible to a specific doctor.
        Logic: Global active options MINUS those the doctor has disabled.
        """
        # Get all option IDs the doctor has explicitly disabled
        disabled_ids = session.exec(
            select(DoctorEnumPreference.enum_option_id)
            .where(
                DoctorEnumPreference.doctor_id == doctor_id,
                DoctorEnumPreference.is_enabled == False
            )
        ).all()
        
        query = (
            select(EnumOption)
            .where(EnumOption.enum_type == enum_type_key)
            .where(EnumOption.is_active == True)
        )
        
        if disabled_ids:
            query = query.where(EnumOption.id.notin_(disabled_ids))
        
        return session.exec(
            query.order_by(EnumOption.sort_order, EnumOption.created_at)
        ).all()
    
    @staticmethod
    def get_all_enum_types_with_doctor_options(
        session: Session,
        doctor_id: UUID
    ) -> dict[str, list[EnumOption]]:
        """
        Get all active enum types with their doctor-filtered options.
        
        Returns a dict mapping enum_type_key -> list of options visible to doctor.
        """
        # Get all active enum types
        enum_types = EnumService.get_all_enum_types(session, active_only=True)
        
        result = {}
        for enum_type in enum_types:
            # Get doctor-filtered options for this type
            options = EnumService.get_doctor_options(session, enum_type.key, doctor_id)
            result[enum_type.key] = options
        
        return result
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    @staticmethod
    def validate_value(
        session: Session,
        enum_type_key: str,
        value: str,
        doctor_id: Optional[UUID] = None
    ) -> bool:
        """
        Validate that a value is valid for an enum type.
        If doctor_id provided, check against doctor-filtered options.
        Otherwise, check against all global active options.
        """
        if doctor_id:
            valid_options = EnumService.get_doctor_options(session, enum_type_key, doctor_id)
        else:
            valid_options = EnumService.get_global_options(session, enum_type_key)
        
        return any(opt.value == value for opt in valid_options)
    
    @staticmethod
    def validate_option_exists(
        session: Session,
        enum_type_key: str,
        value: str
    ) -> tuple[bool, Optional[EnumOption]]:
        """Check if a value exists for an enum type, return the option if found"""
        option = session.exec(
            select(EnumOption)
            .where(
                EnumOption.enum_type == enum_type_key,
                EnumOption.value == value
            )
        ).first()
        return (option is not None, option)
    
    # ========================================================================
    # DOCTOR PREFERENCES
    # ========================================================================
    
    @staticmethod
    def get_doctor_preference(
        session: Session,
        doctor_id: UUID,
        option_id: UUID
    ) -> Optional[DoctorEnumPreference]:
        """Get a doctor's preference for a specific option"""
        return session.exec(
            select(DoctorEnumPreference)
            .where(
                DoctorEnumPreference.doctor_id == doctor_id,
                DoctorEnumPreference.enum_option_id == option_id
            )
        ).first()
    
    @staticmethod
    def set_doctor_preference(
        session: Session,
        doctor_id: UUID,
        option_id: UUID,
        is_enabled: bool
    ) -> DoctorEnumPreference:
        """Set or update a doctor's preference for an option"""
        # Verify option exists
        option = session.get(EnumOption, option_id)
        if not option:
            raise ValueError(f"Option {option_id} not found")
        
        # Get or create preference
        pref = EnumService.get_doctor_preference(session, doctor_id, option_id)
        
        if not pref:
            pref = DoctorEnumPreference(
                doctor_id=doctor_id,
                enum_option_id=option_id,
                is_enabled=is_enabled
            )
            session.add(pref)
        else:
            pref.is_enabled = is_enabled
        
        session.commit()
        session.refresh(pref)
        return pref
    
    @staticmethod
    def get_all_doctor_preferences(
        session: Session,
        doctor_id: UUID,
        enum_type_key: Optional[str] = None
    ) -> list[DoctorEnumPreference]:
        """Get all preferences for a doctor, optionally filtered by enum type"""
        query = select(DoctorEnumPreference).where(
            DoctorEnumPreference.doctor_id == doctor_id
        )
        
        if enum_type_key:
            # Join with EnumOption to filter by type
            query = query.join(EnumOption).where(
                EnumOption.enum_type == enum_type_key
            )
        
        return session.exec(query).all()
