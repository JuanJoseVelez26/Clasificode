"""
Servicio de Validación Incremental y KPIs Automáticas para ClasifiCode

Este módulo implementa un sistema avanzado de monitoreo en tiempo real que:

1. **Registro Automático**: Captura métricas de cada clasificación individual
   incluyendo tiempo de respuesta, confianza, método utilizado y resultados
   de validación contextual.

2. **Buffer Circular**: Mantiene un buffer de las últimas clasificaciones
   para análisis estadístico y cálculo de tendencias.

3. **KPIs Automáticas**: Calcula y actualiza indicadores clave de rendimiento
   cada N clasificaciones (configurable, por defecto cada 10).

4. **Detección de Alertas**: Identifica automáticamente patrones problemáticos
   como baja confianza, tiempos de respuesta altos o alta proporción de
   casos marcados para revisión.

5. **Umbrales Configurables**: Permite ajustar umbrales de alerta según
   los requisitos operativos del sistema.

6. **Integración con Métricas**: Se integra con el MetricsService para
   persistir métricas calculadas en la base de datos.

Características Técnicas:
- Thread-safe para uso concurrente
- Buffer circular con tamaño configurable
- Cálculo de métricas en tiempo real
- Sistema de alertas proactivo
- Integración con sistema de validación contextual

Métricas Calculadas:
- avg_confidence_incremental: Confianza promedio del período
- avg_response_time_incremental: Tiempo de respuesta promedio
- feedback_ratio_incremental: Proporción de casos problemáticos
- total_classifications_incremental: Total de clasificaciones procesadas

Uso:
    >>> from servicios.incremental_validation import incremental_validation
    >>> # El servicio se inicializa automáticamente
    >>> # Registra una clasificación
    >>> incremental_validation.record_classification(
    ...     case_id=123,
    ...     hs_code="0901110000",
    ...     confidence=0.85,
    ...     validation_result={"validation_score": 0.9},
    ...     method="specific_rule",
    ...     duration_s=1.25
    ... )
    >>> # Obtener resumen de rendimiento
    >>> summary = incremental_validation.get_performance_summary(hours_back=24)
    >>> print(f"Confianza promedio: {summary['avg_confidence']:.2f}")
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
from dataclasses import dataclass, field
from servicios.metrics_service import metrics_service

@dataclass
class ClassificationRecord:
    """Registro de una clasificación individual para análisis incremental"""
    case_id: int
    hs_code: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    validation_score: float = 1.0
    validation_result: Dict[str, Any] = field(default_factory=dict)
    method: str = "unknown"  # 'specific_rule', 'rgi', 'fallback'
    is_suspect: bool = False
    requires_review: bool = False
    duration_s: float = 0.0

class IncrementalValidationService:
    """
    Servicio de validación incremental que calcula KPIs automáticamente.
    
    Funcionalidades:
    - Registro automático de métricas por clasificación
    - Cálculo de KPIs promediadas cada 10 clasificaciones
    - Detección de patrones de degradación de rendimiento
    - Alertas automáticas por métricas críticas
    """
    
    def __init__(self, batch_size: int = 10):
        """
        Inicializa el servicio de validación incremental.
        
        Args:
            batch_size: Número de clasificaciones para calcular KPIs promediadas
        """
        self.batch_size = batch_size
        self.classification_buffer = deque(maxlen=batch_size)
        self.lock = threading.Lock()
        self.last_kpi_update = datetime.now()
        self.performance_history = deque(maxlen=100)  # Últimas 100 mediciones
        
        # Umbrales para alertas
        self.thresholds = {
            'min_confidence': 0.6,
            'max_response_time': 10.0,
            'min_validation_score': 0.7,
            'max_error_rate': 0.2
        }
    
    def record_classification(self, case_id: int, hs_code: str,
                              confidence: Optional[float] = None,
                              validation_score: Optional[float] = None,
                              validation_result: Optional[Dict[str, Any]] = None,
                              method: Optional[str] = None,
                              is_suspect: Optional[bool] = None,
                              requires_review: Optional[bool] = None,
                              duration_s: Optional[float] = None) -> None:
        """
        Registra una clasificación individual para análisis incremental.
        
        Args:
            case_id: ID del caso clasificado
            hs_code: Código HS asignado
            confidence: Confianza de la clasificación (opcional)
            validation_score: Score de validación (opcional)
            validation_result: Resultado de validación (opcional)
            method: Método de clasificación usado (opcional)
            is_suspect: Si pertenece a lista de códigos sospechosos
            requires_review: Si requiere revisión humana
            duration_s: Duración de la clasificación en segundos
        """
        try:
            with self.lock:
                safe_confidence = float(confidence) if confidence is not None else 0.0
                safe_validation_score = (
                    float(validation_score)
                    if validation_score is not None
                    else float(validation_result.get('validation_score', 1.0))
                    if validation_result
                    else 1.0
                )
                safe_validation_result = validation_result.copy() if isinstance(validation_result, dict) else {}
                safe_method = method or safe_validation_result.get('method', 'unknown')
                safe_requires_review = bool(requires_review)
                safe_is_suspect = bool(is_suspect)
                safe_duration = float(duration_s) if duration_s is not None else float(safe_validation_result.get('response_time', 0.0) or 0.0)
                
                # Crear registro de clasificación
                record = ClassificationRecord(
                    case_id=case_id,
                    hs_code=hs_code,
                    confidence=safe_confidence,
                    validation_score=safe_validation_score,
                    validation_result=safe_validation_result,
                    method=safe_method,
                    is_suspect=safe_is_suspect,
                    requires_review=safe_requires_review,
                    duration_s=safe_duration
                )
                
                # Agregar al buffer
                self.classification_buffer.append(record)
                
                # Calcular métricas individuales
                response_time = record.duration_s
                
                # Registrar métricas individuales
                try:
                    metrics_service.record_classification_metrics(
                        case_id,
                        record.confidence,
                        response_time,
                        record.validation_score,
                        requires_review=record.requires_review
                    )
                except Exception as metrics_error:
                    logging.warning(f"[IncrementalValidation] Error registrando métricas individuales: {metrics_error}")
                
                # Verificar si es momento de calcular KPIs promediadas
                if len(self.classification_buffer) >= self.batch_size:
                    self._calculate_batch_kpis()
                
                # Verificar alertas
                self._check_alerts(record)
                
        except Exception as e:
            logging.warning(f"[IncrementalValidation] Error registrando clasificación incremental: {e}")
            # No lanzar excepción para no romper el flujo principal
    
    def _calculate_batch_kpis(self) -> None:
        """
        Calcula KPIs promediadas del último lote de clasificaciones.
        """
        try:
            if not self.classification_buffer:
                return
            
            # Calcular métricas del lote
            confidences = [r.confidence for r in self.classification_buffer]
            response_times = [r.duration_s for r in self.classification_buffer]
            validation_scores = [r.validation_score for r in self.classification_buffer]
            
            # Métricas promediadas
            avg_confidence = sum(confidences) / len(confidences)
            avg_response_time = sum(response_times) / len(response_times)
            avg_validation_score = sum(validation_scores) / len(validation_scores)
            
            # Métricas adicionales
            low_confidence_count = sum(1 for c in confidences if c < self.thresholds['min_confidence'])
            slow_response_count = sum(1 for t in response_times if t > self.thresholds['max_response_time'])
            validation_failures = sum(1 for s in validation_scores if s < self.thresholds['min_validation_score'])
            
            # Calcular tasas
            low_confidence_rate = low_confidence_count / len(confidences)
            slow_response_rate = slow_response_count / len(response_times)
            validation_failure_rate = validation_failures / len(validation_scores)
            
            # Crear registro de rendimiento
            performance_record = {
                'timestamp': datetime.now().isoformat(),
                'batch_size': len(self.classification_buffer),
                'avg_confidence': avg_confidence,
                'avg_response_time': avg_response_time,
                'avg_validation_score': avg_validation_score,
                'low_confidence_rate': low_confidence_rate,
                'slow_response_rate': slow_response_rate,
                'validation_failure_rate': validation_failure_rate,
                'method_distribution': self._calculate_method_distribution()
            }
            
            # Agregar al historial
            self.performance_history.append(performance_record)
            
            # Registrar KPIs en base de datos
            self._register_batch_kpis(performance_record)
            
            # Limpiar buffer
            self.classification_buffer.clear()
            self.last_kpi_update = datetime.now()
            
            logging.info(f"[KPIS] KPIs calculadas para lote: confianza={avg_confidence:.3f}, tiempo={avg_response_time:.2f}s")
            
        except Exception as e:
            logging.error(f"[KPIS] Error calculando KPIs del lote: {e}")
    
    def _calculate_method_distribution(self) -> Dict[str, float]:
        """
        Calcula la distribución de métodos de clasificación en el lote.
        
        Returns:
            Diccionario con distribución de métodos
        """
        method_counts = {}
        total = len(self.classification_buffer)
        
        for record in self.classification_buffer:
            method = record.method
            method_counts[method] = method_counts.get(method, 0) + 1
        
        # Convertir a porcentajes
        distribution = {}
        for method, count in method_counts.items():
            distribution[method] = count / total
        
        return distribution
    
    def _register_batch_kpis(self, performance_record: Dict[str, Any]) -> None:
        """
        Registra KPIs del lote en la base de datos.
        
        Args:
            performance_record: Registro de rendimiento del lote
        """
        try:
            # Registrar métricas individuales
            metrics_service.update_kpi('batch_avg_confidence', performance_record['avg_confidence'], {
                'batch_size': performance_record['batch_size'],
                'timestamp': performance_record['timestamp']
            })
            
            metrics_service.update_kpi('batch_avg_response_time', performance_record['avg_response_time'], {
                'batch_size': performance_record['batch_size'],
                'timestamp': performance_record['timestamp']
            })
            
            metrics_service.update_kpi('batch_avg_validation_score', performance_record['avg_validation_score'], {
                'batch_size': performance_record['batch_size'],
                'timestamp': performance_record['timestamp']
            })
            
            metrics_service.update_kpi('low_confidence_rate', performance_record['low_confidence_rate'], {
                'batch_size': performance_record['batch_size'],
                'timestamp': performance_record['timestamp']
            })
            
            metrics_service.update_kpi('slow_response_rate', performance_record['slow_response_rate'], {
                'batch_size': performance_record['batch_size'],
                'timestamp': performance_record['timestamp']
            })
            
            metrics_service.update_kpi('validation_failure_rate', performance_record['validation_failure_rate'], {
                'batch_size': performance_record['batch_size'],
                'timestamp': performance_record['timestamp']
            })
            
        except Exception as e:
            logging.error(f"[KPIS] Error registrando KPIs del lote: {e}")
    
    def _check_alerts(self, record: ClassificationRecord) -> None:
        """
        Verifica si se deben generar alertas basadas en el registro.
        
        Args:
            record: Registro de clasificación a verificar
        """
        try:
            alerts = []
            
            # Verificar confianza baja
            if record.confidence < self.thresholds['min_confidence']:
                alerts.append({
                    'type': 'low_confidence',
                    'value': record.confidence,
                    'threshold': self.thresholds['min_confidence'],
                    'case_id': record.case_id
                })
            
            # Verificar tiempo de respuesta alto
            response_time = record.duration_s
            if response_time > self.thresholds['max_response_time']:
                alerts.append({
                    'type': 'slow_response',
                    'value': response_time,
                    'threshold': self.thresholds['max_response_time'],
                    'case_id': record.case_id
                })
            
            # Verificar fallo de validación
            validation_score = record.validation_score
            if validation_score < self.thresholds['min_validation_score']:
                alerts.append({
                    'type': 'validation_failure',
                    'value': validation_score,
                    'threshold': self.thresholds['min_validation_score'],
                    'case_id': record.case_id
                })
            
            # Registrar alertas
            for alert in alerts:
                self._register_alert(alert)
                
        except Exception as e:
            logging.error(f"[ALERT] Error verificando alertas: {e}")
    
    def _register_alert(self, alert: Dict[str, Any]) -> None:
        """
        Registra una alerta en el sistema.
        
        Args:
            alert: Diccionario con información de la alerta
        """
        try:
            metrics_service.update_kpi('system_alert', 1.0, {
                'alert_type': alert['type'],
                'value': alert['value'],
                'threshold': alert['threshold'],
                'case_id': alert['case_id'],
                'timestamp': datetime.now().isoformat()
            })
            
            logging.info(f"[ALERT] {alert['type']}: valor={alert['value']}, umbral={alert['threshold']}, caso={alert['case_id']}")
            
        except Exception as e:
            logging.error(f"[ALERT] Error registrando alerta: {e}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtiene un resumen del rendimiento del sistema.
        
        Args:
            hours: Número de horas hacia atrás para analizar
            
        Returns:
            Diccionario con resumen de rendimiento
        """
        try:
            # Filtrar registros del período
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_records = [r for r in self.performance_history 
                            if datetime.fromisoformat(r['timestamp']) >= cutoff_time]
            
            if not recent_records:
                return {
                    'period_hours': hours,
                    'total_batches': 0,
                    'avg_confidence': 0.0,
                    'avg_response_time': 0.0,
                    'avg_validation_score': 0.0,
                    'system_status': 'no_data'
                }
            
            # Calcular métricas del período
            total_batches = len(recent_records)
            avg_confidence = sum(r['avg_confidence'] for r in recent_records) / total_batches
            avg_response_time = sum(r['avg_response_time'] for r in recent_records) / total_batches
            avg_validation_score = sum(r['avg_validation_score'] for r in recent_records) / total_batches
            
            # Calcular tasas promedio
            avg_low_confidence_rate = sum(r['low_confidence_rate'] for r in recent_records) / total_batches
            avg_slow_response_rate = sum(r['slow_response_rate'] for r in recent_records) / total_batches
            avg_validation_failure_rate = sum(r['validation_failure_rate'] for r in recent_records) / total_batches
            
            # Determinar estado del sistema
            system_status = 'healthy'
            if avg_confidence < self.thresholds['min_confidence']:
                system_status = 'warning'
            if avg_response_time > self.thresholds['max_response_time']:
                system_status = 'warning'
            if avg_validation_failure_rate > self.thresholds['max_error_rate']:
                system_status = 'critical'
            
            return {
                'period_hours': hours,
                'total_batches': total_batches,
                'avg_confidence': avg_confidence,
                'avg_response_time': avg_response_time,
                'avg_validation_score': avg_validation_score,
                'avg_low_confidence_rate': avg_low_confidence_rate,
                'avg_slow_response_rate': avg_slow_response_rate,
                'avg_validation_failure_rate': avg_validation_failure_rate,
                'system_status': system_status,
                'last_update': self.last_kpi_update.isoformat(),
                'thresholds': self.thresholds
            }
            
        except Exception as e:
            logging.error(f"[KPIS] Error generando resumen de rendimiento: {e}")
            return {
                'period_hours': hours,
                'total_batches': 0,
                'avg_confidence': 0.0,
                'avg_response_time': 0.0,
                'avg_validation_score': 0.0,
                'system_status': 'error'
            }
    
    def force_kpi_calculation(self) -> None:
        """
        Fuerza el cálculo de KPIs con el buffer actual.
        """
        try:
            with self.lock:
                if self.classification_buffer:
                    self._calculate_batch_kpis()
                    logging.info("[KPIS] Cálculo forzado de KPIs completado")
                else:
                    logging.info("[KPIS] No hay clasificaciones en buffer para calcular KPIs")
                    
        except Exception as e:
            logging.error(f"[KPIS] Error en cálculo forzado de KPIs: {e}")
    
    def update_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        """
        Actualiza los umbrales para alertas.
        
        Args:
            new_thresholds: Nuevos umbrales a aplicar
        """
        try:
            self.thresholds.update(new_thresholds)
            logging.info(f"[KPIS] Umbrales actualizados: {new_thresholds}")
            
        except Exception as e:
            logging.error(f"[KPIS] Error actualizando umbrales: {e}")

# Instancia global del servicio de validación incremental
incremental_validation = IncrementalValidationService()
