# utils/availability_service.py
"""
Availability service for handling doctor availability with exceptions.
"""
from datetime import date, time, datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

from sqlmodel import Session, select, and_


def get_available_slots_for_day(
    session: Session,
    doctor_id: uuid.UUID,
    check_date: date,
    slot_duration: int = 30
) -> List[Dict[str, Any]]:
    """
    Get all available time slots for a doctor on a specific date.
    Respects both regular schedule and exceptions.
    
    Args:
        session: Database session
        doctor_id: UUID of the doctor
        check_date: Date to check availability for
        slot_duration: Duration of each slot in minutes (default 30)
    
    Returns:
        List of dicts with 'start_time' and 'end_time' for each available slot
    """
    from models.doctor_availability_model import DoctorAvailability, DayOfWeek
    from models.doctor_availability_exception_model import DoctorAvailabilityException, ExceptionType
    
    # Check for exception first
    exception = session.exec(
        select(DoctorAvailabilityException).where(
            and_(
                DoctorAvailabilityException.doctor_id == doctor_id,
                DoctorAvailabilityException.exception_date == check_date,
                DoctorAvailabilityException.is_active == True
            )
        )
    ).first()
    
    if exception:
        if exception.exception_type in [ExceptionType.UNAVAILABLE, ExceptionType.HOLIDAY]:
            return []  # No slots available
        
        elif exception.exception_type == ExceptionType.CUSTOM_HOURS:
            if not exception.start_time or not exception.end_time:
                return []
            start = exception.start_time
            end = exception.end_time
        else:
            return []
    else:
        # Use regular weekly schedule
        day_number = check_date.weekday()  # 0=Monday, 6=Sunday
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_name = day_names[day_number]
        
        availability = session.exec(
            select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == doctor_id,
                    DoctorAvailability.day_of_week == day_name,
                    DoctorAvailability.is_available == True
                )
            )
        ).first()
        
        if not availability:
            return []
        
        start = availability.start_time
        end = availability.end_time
    
    # Generate slots
    slots = []
    current = datetime.combine(check_date, start)
    end_datetime = datetime.combine(check_date, end)
    
    while current + timedelta(minutes=slot_duration) <= end_datetime:
        slots.append({
            'start_time': current.time(),
            'end_time': (current + timedelta(minutes=slot_duration)).time()
        })
        current += timedelta(minutes=slot_duration)
    
    return slots


def is_doctor_available(
    session: Session,
    doctor_id: uuid.UUID,
    check_date: date,
    check_time: time
) -> bool:
    """
    Check if doctor is available at specific date and time.
    
    Logic:
    1. First check for date-specific exceptions
    2. If exception exists:
       - If UNAVAILABLE or HOLIDAY: return False
       - If CUSTOM_HOURS: check if time is within custom hours
    3. If no exception, fall back to regular weekly schedule
    
    Args:
        session: Database session
        doctor_id: UUID of the doctor
        check_date: Date to check
        check_time: Time to check
    
    Returns:
        bool: True if doctor is available, False otherwise
    """
    from models.doctor_availability_model import DoctorAvailability
    from models.doctor_availability_exception_model import DoctorAvailabilityException, ExceptionType
    
    # Step 1: Check for date-specific exception
    exception = session.exec(
        select(DoctorAvailabilityException).where(
            and_(
                DoctorAvailabilityException.doctor_id == doctor_id,
                DoctorAvailabilityException.exception_date == check_date,
                DoctorAvailabilityException.is_active == True
            )
        )
    ).first()
    
    if exception:
        # Handle different exception types
        if exception.exception_type in [ExceptionType.UNAVAILABLE, ExceptionType.HOLIDAY]:
            return False
        
        elif exception.exception_type == ExceptionType.CUSTOM_HOURS:
            # Check if time falls within custom hours
            if exception.start_time and exception.end_time:
                return exception.start_time <= check_time <= exception.end_time
            return False
    
    # Step 2: No exception found, check regular weekly schedule
    day_number = check_date.weekday()  # 0=Monday, 6=Sunday
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_name = day_names[day_number]
    
    availability = session.exec(
        select(DoctorAvailability).where(
            and_(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.day_of_week == day_name,
                DoctorAvailability.is_available == True
            )
        )
    ).first()
    
    if not availability:
        return False
    
    # Check if time is within working hours
    return availability.start_time <= check_time <= availability.end_time


def get_availability_calendar(
    session: Session,
    doctor_id: uuid.UUID,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Get a calendar view of doctor availability for a date range.
    Shows regular schedule + exceptions.
    
    Args:
        session: Database session
        doctor_id: UUID of the doctor
        start_date: Start date of range
        end_date: End date of range
    
    Returns:
        Dict with dates as keys and availability info as values
    """
    from models.doctor_availability_model import DoctorAvailability
    from models.doctor_availability_exception_model import DoctorAvailabilityException, ExceptionType
    
    calendar = {}
    current_date = start_date
    
    while current_date <= end_date:
        day_number = current_date.weekday()
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_name = day_names[day_number]
        
        # Check for exception
        exception = session.exec(
            select(DoctorAvailabilityException).where(
                and_(
                    DoctorAvailabilityException.doctor_id == doctor_id,
                    DoctorAvailabilityException.exception_date == current_date,
                    DoctorAvailabilityException.is_active == True
                )
            )
        ).first()
        
        if exception:
            calendar[str(current_date)] = {
                'available': exception.exception_type == ExceptionType.CUSTOM_HOURS,
                'type': exception.exception_type.value,
                'start_time': exception.start_time.strftime("%H:%M") if exception.start_time else None,
                'end_time': exception.end_time.strftime("%H:%M") if exception.end_time else None,
                'reason': exception.reason
            }
        else:
            # Regular schedule
            availability = session.exec(
                select(DoctorAvailability).where(
                    and_(
                        DoctorAvailability.doctor_id == doctor_id,
                        DoctorAvailability.day_of_week == day_name,
                        DoctorAvailability.is_available == True
                    )
                )
            ).first()
            
            if availability:
                calendar[str(current_date)] = {
                    'available': True,
                    'type': 'regular',
                    'start_time': availability.start_time.strftime("%H:%M"),
                    'end_time': availability.end_time.strftime("%H:%M"),
                    'reason': None
                }
            else:
                calendar[str(current_date)] = {
                    'available': False,
                    'type': 'none',
                    'start_time': None,
                    'end_time': None,
                    'reason': None
                }
        
        current_date += timedelta(days=1)
    
    return calendar
