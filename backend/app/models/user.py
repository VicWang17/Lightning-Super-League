from sqlalchemy import Column, String, Boolean, DateTime
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_vip = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True) 