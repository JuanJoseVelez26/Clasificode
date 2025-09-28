from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from .base import BaseModel

class User(BaseModel):
    """Modelo de usuario"""
    __tablename__ = 'users'
    
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # admin, auditor, operator
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"
