"""
User-related schemas
"""
from typing import Optional
from pydantic import Field, EmailStr
from datetime import datetime
from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    """Base user schema with common fields"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")


class UserCreate(UserBase):
    """User registration schema"""
    password: str = Field(..., min_length=8, max_length=100, description="密码")


class UserUpdate(BaseSchema):
    """User profile update schema"""
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """User response schema"""
    id: str
    level: int = Field(default=1, description="用户等级")
    experience: int = Field(default=0, description="经验值")
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None


class UserLogin(BaseSchema):
    """User login request schema"""
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiration time in seconds")


class UserWithToken(UserResponse):
    """User info with tokens after login"""
    token: TokenResponse


class UserInToken(BaseSchema):
    """User info embedded in JWT token"""
    id: str
    email: str
    username: str
