"""
General utility functions
"""
import uuid
from datetime import datetime


def generate_uuid() -> str:
    """Generate a unique identifier"""
    return str(uuid.uuid4())


def now() -> datetime:
    """Get current UTC datetime"""
    return datetime.utcnow()


def format_datetime(dt: datetime | None) -> str | None:
    """Format datetime to ISO string"""
    if dt is None:
        return None
    return dt.isoformat()
