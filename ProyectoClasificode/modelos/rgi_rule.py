from sqlalchemy import Column, String, Text, Boolean, Integer
from .base import BaseModel

class RGIRule(BaseModel):
    """Modelo de regla RGI"""
    __tablename__ = 'rgi_rules'
    
    rgi = Column(String(10), nullable=False)  # RGI1, RGI2A, RGI2B, RGI3A, RGI3B, RGI3C, RGI4, RGI5A, RGI5B, RGI6
    description = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<RGIRule(rgi='{self.rgi}', description='{self.description[:50]}...')>"
