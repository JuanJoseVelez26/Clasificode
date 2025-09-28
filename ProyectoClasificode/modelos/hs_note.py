from sqlalchemy import Column, String, Text, Integer
from .base import BaseModel

class HSNote(BaseModel):
    """Modelo de nota del catálogo HS"""
    __tablename__ = 'hs_notes'
    
    scope = Column(String(20), nullable=False)  # SECTION, CHAPTER, HEADING, SUBHEADING
    scope_code = Column(String(20), nullable=False)
    note_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<HSNote(scope='{self.scope}', scope_code='{self.scope_code}', note_number={self.note_number})>"
