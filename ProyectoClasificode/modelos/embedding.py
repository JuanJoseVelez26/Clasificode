from sqlalchemy import Column, String, Integer, UniqueConstraint, Text
from .base import BaseModel

class Embedding(BaseModel):
    """Modelo de embedding para búsqueda vectorial con pgvector"""
    __tablename__ = 'embeddings'
    
    owner_type = Column(String(20), nullable=False)  # hs_item, case
    owner_id = Column(Integer, nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    dim = Column(Integer, nullable=False)
    vector = Column(Text, nullable=False)  # pgvector como texto para compatibilidad
    text_norm = Column(String, nullable=False)
    
    # Constraint único
    __table_args__ = (
        UniqueConstraint('owner_type', 'owner_id', 'provider', 'model', name='uq_embedding_owner'),
    )
    
    def __repr__(self):
        return f"<Embedding(owner_type='{self.owner_type}', owner_id={self.owner_id}, provider='{self.provider}')>"
