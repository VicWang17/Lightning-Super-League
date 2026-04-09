"""
Base schema classes for all API schemas
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ResponseSchema(BaseSchema, Generic[T]):
    """Standard API response wrapper"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[T] = None
    timestamp: datetime = datetime.utcnow()


class PaginationParams(BaseSchema):
    """Pagination query parameters"""
    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated response wrapper"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class ErrorResponse(BaseSchema):
    """Error response schema"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
