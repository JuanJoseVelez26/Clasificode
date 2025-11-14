#!/usr/bin/env python3
"""
Sistema de Aprendizaje Robusto para ClasifiCode

Este módulo implementa un sistema de realimentación efectiva y controlada que permite
mejorar continuamente la precisión del clasificador arancelario HS mediante:

1. **Registro de Feedback**: Almacena correcciones manuales del usuario sobre
   clasificaciones incorrectas, incluyendo comentarios explicativos.

2. **Análisis de Patrones**: Identifica patrones comunes en clasificaciones
   incorrectas para detectar áreas de mejora en el sistema.

3. **Generación de Sugerencias**: Propone nuevas reglas específicas basadas
   en el análisis de errores y feedback acumulado.

4. **Auditoría y Trazabilidad**: Mantiene un historial completo de todas las
   correcciones y sugerencias para auditoría y seguimiento.

5. **Control Humano**: El sistema NO se auto-modifica automáticamente. Todas
   las sugerencias deben ser revisadas y aprobadas por un auditor humano
   antes de ser implementadas.

Características Principales:
- Almacenamiento persistente en archivo JSON local
- Análisis estadístico de patrones de error
- Generación automática de propuestas de reglas
- Sistema de scoring para priorizar sugerencias
- Integración con métricas del sistema para validación

Uso:
    Las funciones de este módulo están diseñadas para ser llamadas desde:
    - Consola de administración
    - Scripts de análisis
    - Notebooks de investigación
    - Endpoints de administración (futuro)

Ejemplo de uso:
    >>> from servicios.learning_system import LearningSystem
    >>> ls = LearningSystem()
    >>> ls.register_feedback(123, "0901110000", "Café sin tostar", "Clasificación correcta")
    >>> suggestions = ls.analyze_misclassifications()
    >>> print(f"Encontrados {len(suggestions)} patrones de mejora")
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import re
from dataclasses import dataclass, field

@dataclass
class FeedbackRecord:
    """Registro de feedback del usuario sobre una clasificación"""
    case_id: int
    input_text: str
    predicted_hs: str
    original_hs: str
    correct_hs: str
    confidence_original: float
    timestamp: datetime
    validation_flags: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)
    rationale: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    requires_review: bool = False

@dataclass
class MisclassificationPattern:
    """Patrón identificado de clasificación incorrecta"""
    pattern_text: str
    original_hs: str
    correct_hs: str
    frequency: int
    confidence_range: Tuple[float, float]
    common_features: Dict[str, Any]
    suggested_rule: Optional[Dict[str, str]]

class LearningSystem:
    """
    Sistema de aprendizaje robusto que analiza errores y genera sugerencias.
    
    Funcionalidades:
    - Registro de feedback del usuario
    - Análisis de patrones de error
    - Generación de sugerencias de reglas
    - Métricas de aprendizaje
    """
    
    def __init__(self, feedback_file: str = "learning_data.json"):
        """
        Inicializa el sistema de aprendizaje.
        
        Args:
            feedback_file: Archivo JSON para almacenar feedback persistente
        """
        self.feedback_file = feedback_file
        self.feedback_records: List[FeedbackRecord] = []
        self.load_feedback_data()
    
    def register_feedback(
        self,
        case_id: int,
        input_text: str,
        predicted_hs: str,
        confidence: float,
        rationale: Optional[Dict[str, Any]] = None,
        original_result: Optional[Dict[str, Any]] = None,
        correct_hs: Optional[str] = None,
        requires_review: bool = False
    ) -> None:
        """
        Registra feedback del usuario o automático sobre una clasificación.
        
        Args:
            case_id: ID del caso clasificado
            input_text: Texto original clasificado
            predicted_hs: Código HS predicho por el sistema
            confidence: Confianza de la predicción
            rationale: Rationale generado por el clasificador (opcional)
            original_result: Resultado completo de la clasificación (opcional)
            correct_hs: Código HS correcto suministrado (opcional)
        """
        try:
            safe_confidence = float(confidence) if confidence is not None else 0.0
            safe_rationale = rationale.copy() if isinstance(rationale, dict) else {}
            safe_result = original_result.copy() if isinstance(original_result, dict) else {}
            
            original_hs = (
                safe_result.get('national_code')
                or safe_result.get('hs6')
                or predicted_hs
                or ''
            )
            validation_flags = safe_result.get('validation_flags', {})
            features = safe_result.get('features', {})
            status = "pending"
            
            resolved_correct_hs = correct_hs or safe_result.get('correct_hs') or "pending_label"
            if resolved_correct_hs == "pending_label":
                status = "pending_review"
            if requires_review:
                status = "pending_review"
            
            feedback = FeedbackRecord(
                case_id=case_id,
                input_text=input_text or "",
                predicted_hs=predicted_hs or "",
                original_hs=original_hs or "",
                correct_hs=resolved_correct_hs,
                confidence_original=safe_confidence,
                timestamp=datetime.now(),
                validation_flags=validation_flags,
                features=features,
                rationale=safe_rationale,
                status=status,
                requires_review=requires_review
            )
            
            self.feedback_records.append(feedback)
            self.save_feedback_data()
            logging.info(f"[LEARNING] Feedback registrado para caso {case_id}: {original_hs} -> {resolved_correct_hs}")
        
        except Exception as e:
            logging.warning(f"[LEARNING] Error registrando feedback para caso {case_id}: {e}")
    
    def analyze_misclassifications(self, min_confidence: float = 0.6) -> List[MisclassificationPattern]:
        """
        Analiza casos con baja confianza o feedback manual para identificar patrones.
        
        Args:
            min_confidence: Confianza mínima para considerar casos problemáticos
            
        Returns:
            Lista de patrones de clasificación incorrecta identificados
        """
        patterns = []
        
        try:
            # Agrupar por patrones de texto similares
            text_patterns = defaultdict(list)
            
            for feedback in self.feedback_records:
                # Crear patrón de texto normalizado
                base_text = feedback.rationale.get('decision') if feedback.rationale else feedback.input_text
                pattern_text = self._normalize_text_pattern(base_text or "")
                text_patterns[pattern_text].append(feedback)
            
            # Analizar cada patrón
            for pattern_text, feedbacks in text_patterns.items():
                if len(feedbacks) >= 2:  # Mínimo 2 casos para considerar patrón
                    pattern = self._analyze_pattern(pattern_text, feedbacks)
                    if pattern:
                        patterns.append(pattern)
            
            # Ordenar por frecuencia
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            
            logging.info(f"[LEARNING] Identificados {len(patterns)} patrones de error")
            return patterns
            
        except Exception as e:
            logging.error(f"[LEARNING] Error analizando patrones: {e}")
            return []
    
    def suggest_rule(self, pattern: MisclassificationPattern) -> Optional[Dict[str, str]]:
        """
        Genera sugerencia de regla específica basada en un patrón de error.
        
        Args:
            pattern: Patrón de clasificación incorrecta
            
        Returns:
            Diccionario con sugerencia de regla o None si no se puede generar
        """
        try:
            # Extraer palabras clave del patrón
            keywords = self._extract_keywords(pattern.pattern_text)
            
            if not keywords:
                return None
            
            # Crear sugerencia de regla
            suggested_rule = {
                'pattern': ' '.join(keywords[:3]),  # Máximo 3 palabras clave
                'hs6': pattern.correct_hs[:6] if len(pattern.correct_hs) >= 6 else pattern.correct_hs,
                'national_code': pattern.correct_hs,
                'title': f"Regla sugerida para: {pattern.pattern_text[:50]}...",
                'confidence': 0.8,  # Confianza moderada para reglas sugeridas
                'source': 'learning_system',
                'frequency': pattern.frequency,
                'last_updated': datetime.now().isoformat()
            }
            
            logging.info(f"[LEARNING] Regla sugerida: {suggested_rule['pattern']} -> {suggested_rule['hs6']}")
            return suggested_rule
            
        except Exception as e:
            logging.error(f"[LEARNING] Error generando sugerencia: {e}")
            return None
    
    def get_learning_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas del sistema de aprendizaje.
        
        Returns:
            Diccionario con métricas de aprendizaje
        """
        try:
            total_feedback = len(self.feedback_records)
            
            if total_feedback == 0:
                return {
                    'total_feedback': 0,
                    'accuracy_trend': 0.0,
                    'common_errors': [],
                    'learning_rate': 0.0
                }
            
            # Calcular tendencia de precisión
            recent_feedback = self.feedback_records[-10:] if total_feedback >= 10 else self.feedback_records
            accuracy_trend = sum(1 for f in recent_feedback if f.original_hs != f.correct_hs) / len(recent_feedback)
            
            # Errores más comunes
            error_counts = Counter()
            for feedback in self.feedback_records:
                if feedback.original_hs != feedback.correct_hs:
                    error_key = f"{feedback.original_hs} -> {feedback.correct_hs}"
                    error_counts[error_key] += 1
            
            common_errors = error_counts.most_common(5)
            
            # Tasa de aprendizaje (mejora en el tiempo)
            learning_rate = self._calculate_learning_rate()
            
            return {
                'total_feedback': total_feedback,
                'accuracy_trend': accuracy_trend,
                'common_errors': common_errors,
                'learning_rate': learning_rate,
                'last_analysis': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"[LEARNING] Error calculando métricas: {e}")
            return {}
    
    def analyze_classification_result(self, case: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Analiza el resultado de una clasificación para aprendizaje automático.
        
        Args:
            case: Datos del caso clasificado
            result: Resultado de la clasificación
        """
        try:
            # Solo registrar casos con baja confianza para análisis
            confidence = result.get('confidence', 0.0)
            if confidence < 0.6:
                logging.info(f"[LEARNING] Caso con baja confianza detectado: {case.get('id')} (confianza: {confidence})")
                
                # Registrar para análisis posterior
                self._record_low_confidence_case(case, result)
                
        except Exception as e:
            logging.error(f"[LEARNING] Error en análisis de aprendizaje: {e}")
    
    def _normalize_text_pattern(self, text: str) -> str:
        """Normaliza texto para crear patrones consistentes"""
        # Convertir a minúsculas y remover caracteres especiales
        normalized = re.sub(r'[^\w\s]', ' ', text.lower())
        # Remover palabras muy comunes
        stop_words = {'el', 'la', 'de', 'del', 'para', 'con', 'por', 'en', 'un', 'una', 'es', 'son'}
        words = [w for w in normalized.split() if w not in stop_words and len(w) > 2]
        return ' '.join(words[:5])  # Máximo 5 palabras clave
    
    def _analyze_pattern(self, pattern_text: str, feedbacks: List[FeedbackRecord]) -> Optional[MisclassificationPattern]:
        """Analiza un patrón específico de feedback"""
        try:
            # Agrupar por códigos HS originales y correctos
            hs_mappings = defaultdict(list)
            confidences = []
            all_features = defaultdict(list)
            
            for feedback in feedbacks:
                key = f"{feedback.original_hs} -> {feedback.correct_hs}"
                hs_mappings[key].append(feedback)
                confidences.append(feedback.confidence_original)
                
                # Agregar features comunes
                for feature, value in feedback.features.items():
                    all_features[feature].append(value)
            
            # Encontrar el mapeo más común
            most_common_mapping = max(hs_mappings.items(), key=lambda x: len(x[1]))
            original_hs, correct_hs = most_common_mapping[0].split(' -> ')
            
            # Calcular features más comunes
            common_features = {}
            for feature, values in all_features.items():
                if values:
                    most_common_value = Counter(values).most_common(1)[0][0]
                    common_features[feature] = most_common_value
            
            return MisclassificationPattern(
                pattern_text=pattern_text,
                original_hs=original_hs,
                correct_hs=correct_hs,
                frequency=len(feedbacks),
                confidence_range=(min(confidences), max(confidences)),
                common_features=common_features,
                suggested_rule=None
            )
            
        except Exception as e:
            logging.error(f"[LEARNING] Error analizando patrón: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave relevantes del texto"""
        # Palabras que indican características importantes
        important_words = []
        words = text.split()
        
        for word in words:
            if len(word) > 3 and word not in {'para', 'con', 'del', 'las', 'los', 'una', 'uno'}:
                important_words.append(word)
        
        return important_words[:5]  # Máximo 5 palabras clave
    
    def _calculate_learning_rate(self) -> float:
        """Calcula la tasa de aprendizaje basada en la mejora en el tiempo"""
        try:
            if len(self.feedback_records) < 10:
                return 0.0
            
            # Dividir en períodos
            mid_point = len(self.feedback_records) // 2
            early_period = self.feedback_records[:mid_point]
            late_period = self.feedback_records[mid_point:]
            
            # Calcular precisión en cada período
            early_accuracy = sum(1 for f in early_period if f.original_hs == f.correct_hs) / len(early_period)
            late_accuracy = sum(1 for f in late_period if f.original_hs == f.correct_hs) / len(late_period)
            
            return late_accuracy - early_accuracy
            
        except Exception as e:
            logging.error(f"[LEARNING] Error calculando tasa de aprendizaje: {e}")
            return 0.0
    
    def _record_low_confidence_case(self, case: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Registra un caso con baja confianza para análisis posterior"""
        try:
            # Crear registro de caso problemático
            problematic_case = {
                'case_id': case.get('id'),
                'timestamp': datetime.now().isoformat(),
                'product_desc': case.get('product_desc', ''),
                'hs_code': result.get('national_code', ''),
                'confidence': result.get('confidence', 0.0),
                'features': result.get('features', {}),
                'validation_flags': result.get('validation_flags', {}),
                'rationale': result.get('rationale', '')
            }
            
            # Guardar en archivo de casos problemáticos
            self._save_problematic_case(problematic_case)
            
        except Exception as e:
            logging.error(f"[LEARNING] Error registrando caso problemático: {e}")
    
    def _save_problematic_case(self, case: Dict[str, Any]) -> None:
        """Guarda un caso problemático en archivo JSON"""
        try:
            problematic_file = "problematic_cases.json"
            
            # Cargar casos existentes
            if os.path.exists(problematic_file):
                with open(problematic_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'problematic_cases': []}
            
            # Agregar nuevo caso
            data['problematic_cases'].append(case)
            
            # Guardar
            with open(problematic_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"[LEARNING] Error guardando caso problemático: {e}")
    
    def load_feedback_data(self):
        """Carga datos de feedback desde archivo JSON"""
        try:
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convertir datos a objetos FeedbackRecord
                self.feedback_records = []
                for record_data in data.get('feedback_records', []):
                    feedback = FeedbackRecord(
                        case_id=record_data['case_id'],
                        input_text=record_data.get('input_text') or record_data.get('user_comment', ''),
                        predicted_hs=record_data.get('predicted_hs', ''),
                        original_hs=record_data.get('original_hs', ''),
                        correct_hs=record_data.get('correct_hs', 'pending_label'),
                        confidence_original=record_data.get('confidence_original', 0.0),
                        timestamp=datetime.fromisoformat(record_data['timestamp']),
                        validation_flags=record_data.get('validation_flags', {}),
                        features=record_data.get('features', {}),
                        rationale=record_data.get('rationale', {}),
                        status=record_data.get('status', 'pending')
                    )
                    self.feedback_records.append(feedback)
                
                logging.info(f"[LEARNING] Cargados {len(self.feedback_records)} registros de feedback")
            else:
                logging.info("[LEARNING] No se encontró archivo de feedback, iniciando vacío")
                
        except Exception as e:
            logging.error(f"[LEARNING] Error cargando feedback: {e}")
            self.feedback_records = []
    
    def save_feedback_data(self):
        """Guarda datos de feedback en archivo JSON"""
        try:
            data = {
                'feedback_records': [],
                'last_updated': datetime.now().isoformat()
            }
            
            for feedback in self.feedback_records:
                record_data = {
                    'case_id': feedback.case_id,
                    'input_text': feedback.input_text,
                    'predicted_hs': feedback.predicted_hs,
                    'original_hs': feedback.original_hs,
                    'correct_hs': feedback.correct_hs,
                    'confidence_original': feedback.confidence_original,
                    'timestamp': feedback.timestamp.isoformat(),
                    'validation_flags': feedback.validation_flags,
                    'features': feedback.features,
                    'rationale': feedback.rationale,
                    'status': feedback.status
                }
                data['feedback_records'].append(record_data)
            
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"[LEARNING] Feedback guardado: {len(self.feedback_records)} registros")
            
        except Exception as e:
            logging.error(f"[LEARNING] Error guardando feedback: {e}")

# Instancia global del sistema de aprendizaje
learning_system = LearningSystem()