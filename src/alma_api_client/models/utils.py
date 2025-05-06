"""Utility functions for parsing various data types safely."""

import warnings
# noinspection PyUnresolvedReferences
from datetime import datetime, date, timezone
from typing import Optional, Union, Any


def parse_datetime_optional(value: Optional[str]) -> Union[datetime, str, None]:
    """
    Safely parse ISO format datetime strings, preserving timezone.
    Returns original string value if parsing fails.
    """
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            return value

        if value.endswith('Z'):
            naive_dt = datetime.fromisoformat(value.replace('Z', ''))
            aware_dt = naive_dt.replace(tzinfo=timezone.utc)
            return aware_dt
        else:
            dt = datetime.fromisoformat(value)
            return dt
    except (ValueError, TypeError):
        warnings.warn(f"Could not parse datetime string: {value}", UserWarning)
        return value


def parse_date_optional(value: Optional[str]) -> Union[date, str, None]:
    """
    Safely parse ISO format date strings (YYYY-MM-DD).
    Returns original string value if parsing fails.
    """
    if value is None:
        return None
    try:
        if isinstance(value, date):
            return value

        if isinstance(value, str):
            if 'T' in value:
                value = value.split('T')[0]
            if ' ' in value:
                value = value.split(' ')[0]
        else:
            return value

        d = date.fromisoformat(value)
        return d
    except (ValueError, TypeError):
        warnings.warn(f"Could not parse date string: {value}", UserWarning)
        return value


def parse_boolean_optional(value: Union[str, bool, None]) -> Union[bool, Any, None]:
    """
    Safely parse common boolean strings ('true'/'false'), handling None and actual bools.
    Returns original value if input is not a recognized boolean string, bool, or None.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low_val = value.lower()
        if low_val in ('true', 't', 'yes', 'y', '1', 'on'):
            return True
        if low_val in ('false', 'f', 'no', 'n', '0', 'off'):
            return False
        warnings.warn(f"Could not parse boolean value: {value}", UserWarning)
        return value
    return value
