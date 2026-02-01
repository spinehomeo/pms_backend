"""
Centralized datetime utilities for UTC timezone-aware operations.

This module provides helper functions to ensure all datetime objects
in the application are timezone-aware (UTC) to avoid the common
"can't compare offset-naive and offset-aware" error.

Usage:
    from utils.time import utc_now
    
    created_at = utc_now()
    timestamp = utc_now().isoformat()
    today = utc_now().date()
"""

from datetime import datetime, date, timezone


def utc_now() -> datetime:
    """
    Get the current UTC time as a timezone-aware datetime object.
    
    Returns:
        datetime: Current time in UTC with timezone info
        
    Example:
        >>> from utils.time import utc_now
        >>> now = utc_now()
        >>> print(now)
        2026-02-01T15:30:45.123456+00:00
    """
    return datetime.now(timezone.utc)


def utc_today() -> date:
    """
    Get today's date (UTC).
    
    Returns:
        date: Today's date in UTC
        
    Example:
        >>> from utils.time import utc_today
        >>> today = utc_today()
        >>> print(today)
        2026-02-01
    """
    return utc_now().date()


def utc_isoformat() -> str:
    """
    Get current UTC time in ISO 8601 format string.
    
    Returns:
        str: Current time in ISO 8601 format with UTC timezone
        
    Example:
        >>> from utils.time import utc_isoformat
        >>> ts = utc_isoformat()
        >>> print(ts)
        2026-02-01T15:30:45.123456+00:00
    """
    return utc_now().isoformat()
