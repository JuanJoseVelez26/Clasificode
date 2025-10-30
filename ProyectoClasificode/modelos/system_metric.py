"""
Modelo para métricas del sistema ClasifiCode

Este módulo define la tabla system_metrics para almacenar indicadores técnicos
calculados por el backend, no estadísticas de negocio.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from .base import Base

class SystemMetric(Base):
    """
    Tabla para almacenar métricas técnicas del sistema ClasifiCode.
    
    Campos:
    - id: Identificador único
    - metric_name: Nombre de la métrica
    - metric_value: Valor numérico de la métrica
    - context: Contexto adicional en formato JSON
    - created_at: Timestamp de creación
    """
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    context = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemMetric(id={self.id}, name='{self.metric_name}', value={self.metric_value})>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario para serialización JSON"""
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'context': self.context,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
