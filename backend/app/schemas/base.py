"""
Base Pydantic schemas
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with ORM mode"""
    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(BaseSchema):
    """Base response schema with common fields"""
    id: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseSchema):
    """Simple message response"""
    message: str
