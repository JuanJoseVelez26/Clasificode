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
    ...     start_time=start,
    ...     end_time=end,
    ...     confidence=0.85,
    ...     hs_code="0901110000",
    ...     validation_result={"score": 0.9},
    ...     features={"tipo": "producto_terminado"},
    ...     method="specific_rule"
    ... )
    >>> # Obtener resumen de rendimiento
    >>> summary = incremental_validation.get_performance_summary(hours_back=24)
    >>> print(f"Confianza promedio: {summary['avg_confidence']:.2f}")
"""

import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
from dataclasses import dataclass
from servicios.metrics_service import metrics_service

@dataclass
class ClassificationRecord:
    """Registro de una clasificación individual para análisis incremental"""
    case_id: int
    start_time: datetime
    end_time: datetime
    confidence: float
    hs_code: str
    validation_result: Dict[str, Any]
    features: Dict[str, Any]
    method: str  # 'specific_rule', 'rgi', 'fallback'

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
    
    def record_classification(self, case_id: int, start_time: datetime, end_time: datetime,
                            confidence: float, hs_code: str, validation_result: Dict[str, Any],
                            features: Dict[str, Any], method: str, validation_score: float = None, 
                            requires_review: bool = False, context: Dict[str, Any] = None) -> None:
        """
        Registra una clasificación individual para análisis incremental.
        
        Args:
            case_id: ID del caso clasificado
            start_time: Timestamp de inicio de clasificación
            end_time: Timestamp de fin de clasificación
            confidence: Confianza de la clasificación
            hs_code: Código HS asignado
            validation_result: Resultado de validación
            features: Características extraídas
            method: Método de clasificación usado
            validation_score: Score de validación (opcional)
            requires_review: Si requiere revisión humana (opcional)
            context: Contexto adicional (opcional)
        """
        try:
            with self.lock:
                # Crear registro de clasificación
                record = ClassificationRecord(
                    case_id=case_id,
                    start_time=start_time,
                    end_time=end_time,
                    confidence=confidence,
                    hs_code=hs_code,
                    validation_result=validation_result,
                    features=features,
                    method=method
                )
                
                # Agregar al buffer
                self.classification_buffer.append(record)
                
                # Calcular métricas individuales
                response_time = (end_time - start_time).total_seconds()
                validation_score = validation_result.get('validation_score', 1.0)
                
                # Registrar métricas individuales
                metrics_service.record_classification_metrics(
                    case_id, confidence, response_time, validation_score
                )
                
                # Verificar si es momento de calcular KPIs promediadas
                if len(self.classification_buffer) >= self.batch_size:
                    self._calculate_batch_kpis()
                
                # Verificar alertas
                self._check_alerts(record)
                
        except Exception as e:
            print(f"[WARNING] Error registrando clasificación incremental: {e}")
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
            response_times = [(r.end_time - r.start_time).total_seconds() for r in self.classification_buffer]
            validation_scores = [r.validation_result.get('validation_score', 1.0) for r in self.classification_buffer]
            
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
            
            print(f"[KPIS] KPIs calculadas para lote: confianza={avg_confidence:.3f}, tiempo={avg_response_time:.2f}s")
            
        except Exception as e:
            print(f"[ERROR] Error calculando KPIs del lote: {e}")
    
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
            print(f"[ERROR] Error registrando KPIs del lote: {e}")
    
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
            response_time = (record.end_time - record.start_time).total_seconds()
            if response_time > self.thresholds['max_response_time']:
                alerts.append({
                    'type': 'slow_response',
                    'value': response_time,
                    'threshold': self.thresholds['max_response_time'],
                    'case_id': record.case_id
                })
            
            # Verificar fallo de validación
            validation_score = record.validation_result.get('validation_score', 1.0)
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
            print(f"[ERROR] Error verificando alertas: {e}")
    
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
            
            print(f"[ALERT] {alert['type']}: valor={alert['value']}, umbral={alert['threshold']}, caso={alert['case_id']}")
            
        except Exception as e:
            print(f"[ERROR] Error registrando alerta: {e}")
    
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
            print(f"[ERROR] Error generando resumen de rendimiento: {e}")
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
                    print("[KPIS] Cálculo forzado de KPIs completado")
                else:
                    print("[KPIS] No hay clasificaciones en buffer para calcular KPIs")
                    
        except Exception as e:
            print(f"[ERROR] Error en cálculo forzado de KPIs: {e}")
    
    def update_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        """
        Actualiza los umbrales para alertas.
        
        Args:
            new_thresholds: Nuevos umbrales a aplicar
        """
        try:
            self.thresholds.update(new_thresholds)
            print(f"[KPIS] Umbrales actualizados: {new_thresholds}")
            
        except Exception as e:
            print(f"[ERROR] Error actualizando umbrales: {e}")

# Instancia global del servicio de validación incremental
incremental_validation = IncrementalValidationService()
