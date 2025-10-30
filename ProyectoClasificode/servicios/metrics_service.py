"""
Servicio de Métricas del Sistema ClasifiCode

Este módulo implementa un sistema completo de métricas técnicas para monitorear
el rendimiento y la salud del clasificador arancelario HS. Proporciona:

1. **Registro de Métricas**: Almacena métricas individuales en base de datos
   PostgreSQL con contexto temporal y metadatos.

2. **Consultas Históricas**: Permite consultar métricas por períodos específicos
   para análisis de tendencias y evolución del sistema.

3. **Cálculo de KPIs**: Genera indicadores clave de rendimiento como:
   - Precisión promedio del sistema
   - Confianza promedio de clasificaciones
   - Tiempo de respuesta promedio
   - Ratio de feedback/correcciones manuales

4. **Reportes Automáticos**: Genera reportes periódicos para administradores
   y auditores del sistema.

5. **Integración con Validación Incremental**: Se integra con el sistema de
   validación incremental para actualizar métricas automáticamente.

Métricas Principales:
- accuracy_test_set: Precisión en conjunto de pruebas
- avg_confidence: Confianza promedio de clasificaciones
- avg_response_time: Tiempo de respuesta promedio
- feedback_ratio: Proporción de casos que requieren corrección manual
- total_classifications: Total de clasificaciones procesadas
- validation_score: Score promedio de validación contextual

Uso:
    >>> from servicios.metrics_service import MetricsService
    >>> ms = MetricsService()
    >>> ms.record_metric('accuracy_test_set', 0.92, {'test_size': 100})
    >>> kpis = ms.get_latest_kpis(days=7)
    >>> print(f"Precisión última semana: {kpis.get('accuracy_test_set', 0):.2f}")
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from modelos.system_metric import SystemMetric
from servicios.control_conexion import ControlConexion

class MetricsService:
    """
    Servicio para gestionar métricas técnicas del sistema.
    
    Funcionalidades:
    - Registrar métricas individuales
    - Consultar métricas históricas
    - Calcular promedios y tendencias
    - Generar reportes de KPIs
    """
    
    def __init__(self):
        """Inicializa el servicio de métricas"""
        self.cc = ControlConexion()
    
    def update_kpi(self, name: str, value: float, context: Dict[str, Any] = None) -> bool:
        """
        Registra una métrica KPI en la base de datos.
        
        Args:
            name: Nombre de la métrica
            value: Valor numérico de la métrica
            context: Contexto adicional en formato JSON
            
        Returns:
            True si se registró exitosamente, False en caso contrario
        """
        try:
            # Crear nueva métrica
            metric = SystemMetric(
                metric_name=name,
                metric_value=float(value),
                context=context or {},
                created_at=datetime.utcnow()
            )
            
            # Guardar en base de datos usando context manager
            with self.cc.get_session() as session:
                session.add(metric)
                session.commit()
            
            print(f"[METRICS] Métrica registrada: {name} = {value}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error registrando métrica {name}: {e}")
            return False
    
    def get_latest_kpis(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtiene las métricas más recientes del sistema.
        
        Args:
            hours: Número de horas hacia atrás para consultar
            
        Returns:
            Diccionario con las métricas más recientes
        """
        try:
            # Calcular timestamp límite
            limit_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Consultar métricas recientes usando context manager
            with self.cc.get_session() as session:
                metrics = session.query(SystemMetric)\
                    .filter(SystemMetric.created_at >= limit_time)\
                    .order_by(desc(SystemMetric.created_at))\
                    .all()
            
            # Agrupar por nombre de métrica
            kpis = {}
            for metric in metrics:
                metric_name = metric.metric_name
                if metric_name not in kpis:
                    kpis[metric_name] = {
                        'latest_value': metric.metric_value,
                        'latest_context': metric.context,
                        'latest_timestamp': metric.created_at.isoformat(),
                        'count': 1
                    }
                else:
                    kpis[metric_name]['count'] += 1
            
            return kpis
            
        except Exception as e:
            print(f"[ERROR] Error obteniendo KPIs: {e}")
            return {}
    
    def record_classification_metrics(self, case_id: int, confidence: float, response_time: float, validation_score: float) -> bool:
        """
        Registra métricas específicas de una clasificación individual.
        
        Args:
            case_id: ID del caso clasificado
            confidence: Nivel de confianza de la clasificación
            response_time: Tiempo de respuesta en segundos
            validation_score: Score de validación contextual
            
        Returns:
            True si se registró exitosamente, False en caso contrario
        """
        try:
            # Registrar métrica de clasificación individual
            self.update_kpi(
                'classification_event',
                confidence,
                {
                    'case_id': case_id,
                    'response_time': response_time,
                    'validation_score': validation_score,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            # Registrar métricas agregadas
            self.update_kpi('avg_confidence', confidence, {'case_id': case_id})
            self.update_kpi('avg_response_time', response_time, {'case_id': case_id})
            self.update_kpi('validation_score', validation_score, {'case_id': case_id})
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error registrando métricas de clasificación: {e}")
            return False
    
    def get_metric_trend(self, metric_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtiene la tendencia de una métrica específica.
        
        Args:
            metric_name: Nombre de la métrica
            days: Número de días hacia atrás
            
        Returns:
            Lista de valores históricos de la métrica
        """
        try:
            session = self.cc.get_session()
            
            # Calcular timestamp límite
            limit_time = datetime.utcnow() - timedelta(days=days)
            
            # Consultar métricas históricas
            metrics = session.query(SystemMetric)\
                .filter(SystemMetric.metric_name == metric_name)\
                .filter(SystemMetric.created_at >= limit_time)\
                .order_by(SystemMetric.created_at)\
                .all()
            
            session.close()
            
            # Convertir a lista de diccionarios
            trend_data = []
            for metric in metrics:
                trend_data.append({
                    'timestamp': metric.created_at.isoformat(),
                    'value': metric.metric_value,
                    'context': metric.context
                })
            
            return trend_data
            
        except Exception as e:
            print(f"[ERROR] Error obteniendo tendencia de {metric_name}: {e}")
            return []
    
    def calculate_average_confidence(self, hours: int = 24) -> float:
        """
        Calcula la confianza promedio de las clasificaciones recientes.
        
        Args:
            hours: Número de horas hacia atrás para calcular
            
        Returns:
            Confianza promedio
        """
        try:
            session = self.cc.get_session()
            
            # Calcular timestamp límite
            limit_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Consultar métricas de confianza
            avg_confidence = session.query(func.avg(SystemMetric.metric_value))\
                .filter(SystemMetric.metric_name == 'classification_confidence')\
                .filter(SystemMetric.created_at >= limit_time)\
                .scalar()
            
            session.close()
            
            return float(avg_confidence) if avg_confidence else 0.0
            
        except Exception as e:
            print(f"[ERROR] Error calculando confianza promedio: {e}")
            return 0.0
    
    def calculate_average_response_time(self, hours: int = 24) -> float:
        """
        Calcula el tiempo promedio de respuesta de las clasificaciones.
        
        Args:
            hours: Número de horas hacia atrás para calcular
            
        Returns:
            Tiempo promedio de respuesta en segundos
        """
        try:
            session = self.cc.get_session()
            
            # Calcular timestamp límite
            limit_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Consultar métricas de tiempo de respuesta
            avg_time = session.query(func.avg(SystemMetric.metric_value))\
                .filter(SystemMetric.metric_name == 'response_time')\
                .filter(SystemMetric.created_at >= limit_time)\
                .scalar()
            
            session.close()
            
            return float(avg_time) if avg_time else 0.0
            
        except Exception as e:
            print(f"[ERROR] Error calculando tiempo promedio: {e}")
            return 0.0
    
    def get_feedback_ratio(self, hours: int = 24) -> float:
        """
        Calcula la proporción de casos con corrección manual.
        
        Args:
            hours: Número de horas hacia atrás para calcular
            
        Returns:
            Proporción de casos con feedback (0.0 a 1.0)
        """
        try:
            session = self.cc.get_session()
            
            # Calcular timestamp límite
            limit_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Contar total de clasificaciones
            total_classifications = session.query(func.count(SystemMetric.id))\
                .filter(SystemMetric.metric_name == 'classification_completed')\
                .filter(SystemMetric.created_at >= limit_time)\
                .scalar()
            
            # Contar casos con feedback
            feedback_cases = session.query(func.count(SystemMetric.id))\
                .filter(SystemMetric.metric_name == 'user_feedback')\
                .filter(SystemMetric.created_at >= limit_time)\
                .scalar()
            
            session.close()
            
            if total_classifications == 0:
                return 0.0
            
            return float(feedback_cases) / float(total_classifications)
            
        except Exception as e:
            print(f"[ERROR] Error calculando proporción de feedback: {e}")
            return 0.0
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen del estado de salud del sistema.
        
        Returns:
            Diccionario con métricas clave del sistema
        """
        try:
            # Calcular métricas clave
            avg_confidence = self.calculate_average_confidence(24)
            avg_response_time = self.calculate_average_response_time(24)
            feedback_ratio = self.get_feedback_ratio(24)
            
            # Obtener KPIs recientes
            recent_kpis = self.get_latest_kpis(24)
            
            # Calcular precisión estimada (basada en confianza y feedback)
            estimated_accuracy = avg_confidence * (1.0 - feedback_ratio)
            
            return {
                'accuracy_test_set': estimated_accuracy,
                'avg_confidence': avg_confidence,
                'avg_response_time': avg_response_time,
                'feedback_ratio': feedback_ratio,
                'system_status': 'healthy' if avg_confidence > 0.7 and avg_response_time < 5.0 else 'warning',
                'last_updated': datetime.utcnow().isoformat(),
                'recent_metrics': recent_kpis
            }
            
        except Exception as e:
            print(f"[ERROR] Error generando resumen de salud: {e}")
            return {
                'accuracy_test_set': 0.0,
                'avg_confidence': 0.0,
                'avg_response_time': 0.0,
                'feedback_ratio': 0.0,
                'system_status': 'error',
                'last_updated': datetime.utcnow().isoformat(),
                'recent_metrics': {}
            }
    
    def record_classification_metrics(self, case_id: int, confidence: float, 
                                     response_time: float, validation_score: float) -> None:
        """
        Registra métricas de una clasificación individual.
        
        Args:
            case_id: ID del caso clasificado
            confidence: Confianza de la clasificación
            response_time: Tiempo de respuesta en segundos
            validation_score: Score de validación
        """
        try:
            # Registrar confianza
            self.update_kpi('classification_confidence', confidence, {
                'case_id': case_id,
                'type': 'individual'
            })
            
            # Registrar tiempo de respuesta
            self.update_kpi('response_time', response_time, {
                'case_id': case_id,
                'type': 'individual'
            })
            
            # Registrar score de validación
            self.update_kpi('validation_score', validation_score, {
                'case_id': case_id,
                'type': 'individual'
            })
            
            # Registrar clasificación completada
            self.update_kpi('classification_completed', 1.0, {
                'case_id': case_id,
                'confidence': confidence,
                'response_time': response_time
            })
            
        except Exception as e:
            print(f"[ERROR] Error registrando métricas de clasificación: {e}")
    
    def record_user_feedback(self, case_id: int, feedback_type: str) -> None:
        """
        Registra feedback del usuario.
        
        Args:
            case_id: ID del caso
            feedback_type: Tipo de feedback ('correction', 'approval', 'rejection')
        """
        try:
            self.update_kpi('user_feedback', 1.0, {
                'case_id': case_id,
                'feedback_type': feedback_type,
                'type': 'feedback'
            })
            
        except Exception as e:
            print(f"[ERROR] Error registrando feedback: {e}")

# Instancia global del servicio de métricas
metrics_service = MetricsService()
