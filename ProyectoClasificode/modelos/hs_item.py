from sqlalchemy import Column, String, Text, Integer, SmallInteger
from .base import BaseModel

class HSItem(BaseModel):
    """Modelo de item del catálogo HS"""
    __tablename__ = 'hs_items'
    
    hs_code = Column(String(20), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    keywords = Column(Text)
    level = Column(SmallInteger, nullable=False)
    chapter = Column(SmallInteger, nullable=False)
    parent_code = Column(String(20))
    
    def __repr__(self):
        return f"<HSItem(hs_code='{self.hs_code}', title='{self.title[:50]}...')>"
