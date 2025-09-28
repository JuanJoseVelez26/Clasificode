from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel

class Validation(BaseModel):
    """Modelo de validación de casos"""
    __tablename__ = 'validations'
    
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    validator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    final_hs_code = Column(String(20), nullable=False)
    comment = Column(Text)
    
    # Relaciones
    case = relationship("Case", back_populates="validations")
    validator = relationship("User", backref="validations")
    
    def __repr__(self):
        return f"<Validation(case_id={self.case_id}, final_hs_code='{self.final_hs_code}')>"
