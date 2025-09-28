from sqlalchemy import Column, String, Text, Integer, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel

class Candidate(BaseModel):
    """Modelo de candidato para clasificación"""
    __tablename__ = 'candidates'
    
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    hs_code = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    confidence = Column(Float, nullable=False)  # 0..1
    rationale = Column(Text)
    legal_refs_json = Column(Text)  # JSONB en PostgreSQL
    rank = Column(Integer, nullable=False)
    
    # Relaciones
    case = relationship("Case", back_populates="candidates")
    
    # Constraint único
    __table_args__ = (
        UniqueConstraint('case_id', 'rank', name='uq_case_rank'),
    )
    
    def __repr__(self):
        return f"<Candidate(hs_code='{self.hs_code}', confidence={self.confidence}, rank={self.rank})>"
