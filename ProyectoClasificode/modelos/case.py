from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Case(BaseModel):
    """Modelo de caso legal"""
    __tablename__ = 'cases'
    
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), nullable=False)  # open, validated, rejected
    product_title = Column(String(200), nullable=False)
    product_desc = Column(Text)
    attrs_json = Column(JSON)  # JSONB en PostgreSQL
    closed_at = Column(DateTime)
    
    # Relaciones
    creator = relationship("User", backref="created_cases")
    candidates = relationship("Candidate", back_populates="case", cascade="all, delete-orphan")
    validations = relationship("Validation", back_populates="case", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Case(id={self.id}, status='{self.status}', product_title='{self.product_title}')>"
