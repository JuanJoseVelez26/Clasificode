#!/usr/bin/env python3
"""
Integración del sistema de aprendizaje con la aplicación principal
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from .learning_system import LearningSystem

class LearningIntegration:
    """Integra el sistema de aprendizaje con la aplicación principal"""
    
    def __init__(self):
        self.learning_system = LearningSystem()
        self.learning_data_file = "learning_data.json"
        self.load_learning_data()
    
    def load_learning_data(self):
        """Carga los datos de aprendizaje existentes"""
        # El LearningSystem ya carga automáticamente los datos en su constructor
        logging.info(f"[LEARNING] Sistema de aprendizaje inicializado: {len(self.learning_system.feedback_records)} registros de feedback")
    
    def save_learning_data(self):
        """Guarda los datos de aprendizaje"""
        self.learning_system.save_feedback_data()
        logging.info("[LEARNING] Datos de aprendizaje guardados")
    
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
        Registra feedback en el sistema de aprendizaje sin interrumpir el flujo.
        """
        try:
            self.learning_system.register_feedback(
                case_id=case_id,
                input_text=input_text,
                predicted_hs=predicted_hs,
                confidence=confidence,
                rationale=rationale,
                original_result=original_result,
                correct_hs=correct_hs,
                requires_review=requires_review
            )
        except Exception as e:
            logging.warning(f"[LEARNING] Error registrando feedback (case_id={case_id}): {str(e)}")
    
    def analyze_classification_result(self, case: Dict[str, Any], result: Dict[str, Any], 
                                    expected_hs: Optional[str] = None):
        
        description = f"{case.get('product_title', '')} {case.get('product_desc', '')}".strip()
        predicted_hs = result.get('national_code', '')
        predicted_title = result.get('title', '')
        
        if expected_hs:
            # Tenemos el resultado esperado - analizar si fue correcto o incorrecto
            is_correct = predicted_hs.replace('.', '') == expected_hs.replace('.', '')
            
            if is_correct:
                self.learning_system.analyze_classification_success(
                    description, predicted_hs, predicted_title
                )
                logging.info(f"[LEARNING] Clasificación correcta analizada: {predicted_hs}")
            else:
                self.learning_system.analyze_classification_error(
                    description, expected_hs, predicted_hs, predicted_title
                )
                logging.warning(f"[LEARNING] Error de clasificación analizado: {expected_hs} -> {predicted_hs}")
        else:
            # No tenemos resultado esperado - solo registrar éxito
            self.learning_system.analyze_classification_success(
                description, predicted_hs, predicted_title
            )
            logging.debug(f"[LEARNING] Clasificación registrada: {predicted_hs}")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema de aprendizaje"""
        return {
            'error_patterns_count': len(self.learning_system.error_patterns),
            'success_patterns_count': len(self.learning_system.success_patterns),
            'learned_rules_count': len(self.learning_system.learned_rules),
            'total_errors': sum(len(patterns) for patterns in self.learning_system.error_patterns.values()),
            'total_successes': sum(len(patterns) for patterns in self.learning_system.success_patterns.values())
        }
    
    def generate_improvement_suggestions(self) -> List[str]:
        """Genera sugerencias de mejora basadas en los patrones de error"""
        suggestions = []
        
        # Analizar patrones de error más comunes
        error_counts = {}
        for error_type, patterns in self.learning_system.error_patterns.items():
            error_counts[error_type] = len(patterns)
        
        # Ordenar por frecuencia
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        for error_type, count in sorted_errors[:5]:  # Top 5 errores
            if count >= 2:  # Solo errores que ocurren múltiples veces
                suggestions.append(f"Error frecuente: {error_type} ({count} casos)")
        
        return suggestions

# Instancia global del sistema de aprendizaje integrado
learning_integration = LearningIntegration()
