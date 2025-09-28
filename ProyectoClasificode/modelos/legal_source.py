from sqlalchemy import Column, String, Text, DateTime, LargeBinary
from .base import BaseModel

class LegalSource(BaseModel):
    """Modelo de fuente legal"""
    __tablename__ = 'legal_sources'
    
    source_type = Column(String(20), nullable=False)  # RGI, NOTA, RESOLUCION, MANUAL, OTRO
    ref_code = Column(String(100), nullable=False)
    url = Column(String(500))
    fetched_at = Column(DateTime)
    content_hash = Column(String(64))
    summary = Column(Text)
    fetched_by = Column(Text)
    raw_html = Column(LargeBinary)
    
    def __repr__(self):
        return f"<LegalSource(source_type='{self.source_type}', ref_code='{self.ref_code}')>"
