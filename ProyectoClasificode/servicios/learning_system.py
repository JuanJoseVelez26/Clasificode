#!/usr/bin/env python3
"""
Sistema de aprendizaje automático para mejorar la precisión del clasificador
"""

import json
import logging
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
import re

class LearningSystem:
    def __init__(self):
        self.error_patterns = defaultdict(list)
        self.success_patterns = defaultdict(list)
        self.product_categories = defaultdict(list)
        self.learned_rules = {}
        
    def analyze_classification_error(self, description: str, expected_hs: str, 
                                   predicted_hs: str, predicted_title: str):
        """Analiza un error de clasificación para aprender patrones"""
        
        # Extraer palabras clave de la descripción
        keywords = self._extract_keywords(description)
        
        # Categorizar el error
        error_type = self._categorize_error(expected_hs, predicted_hs)
        
        # Guardar patrón de error
        error_pattern = {
            'keywords': keywords,
            'expected_hs': expected_hs,
            'predicted_hs': predicted_hs,
            'predicted_title': predicted_title,
            'error_type': error_type,
            'description': description
        }
        
        self.error_patterns[error_type].append(error_pattern)
        
        # Generar regla específica si es necesario
        self._generate_specific_rule(error_pattern)
        
    def analyze_classification_success(self, description: str, predicted_hs: str, 
                                     predicted_title: str):
        """Analiza una clasificación exitosa para reforzar patrones"""
        
        keywords = self._extract_keywords(description)
        
        success_pattern = {
            'keywords': keywords,
            'predicted_hs': predicted_hs,
            'predicted_title': predicted_title,
            'description': description
        }
        
        self.success_patterns[predicted_hs].append(success_pattern)
        
    def _extract_keywords(self, description: str) -> List[str]:
        """Extrae palabras clave importantes de la descripción"""
        # Normalizar texto
        text = description.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Palabras importantes (excluir stop words)
        stop_words = {'de', 'la', 'el', 'en', 'con', 'para', 'del', 'los', 'las', 'un', 'una', 'y', 'o'}
        
        words = text.split()
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return keywords
    
    def _categorize_error(self, expected_hs: str, predicted_hs: str) -> str:
        """Categoriza el tipo de error de clasificación"""
        
        expected_chapter = expected_hs[:2] if len(expected_hs) >= 2 else expected_hs
        predicted_chapter = predicted_hs[:2] if len(predicted_hs) >= 2 else predicted_hs
        
        if expected_chapter != predicted_chapter:
            return f"wrong_chapter_{expected_chapter}_to_{predicted_chapter}"
        else:
            return f"wrong_subchapter_{expected_hs}_to_{predicted_hs}"
    
    def _generate_specific_rule(self, error_pattern: Dict[str, Any]):
        """Genera reglas específicas basadas en patrones de error"""
        
        keywords = error_pattern['keywords']
        expected_hs = error_pattern['expected_hs']
        description = error_pattern['description']
        
        # Crear regla específica
        rule_key = '_'.join(keywords[:3])  # Usar primeras 3 palabras clave
        
        if rule_key not in self.learned_rules:
            self.learned_rules[rule_key] = {
                'hs6': expected_hs[:6],
                'national_code': expected_hs,
                'title': f'Producto específico: {description[:50]}...',
                'keywords': keywords,
                'confidence': 0.9
            }
    
    def generate_improved_rules(self) -> Dict[str, Any]:
        """Genera reglas mejoradas basadas en el análisis de errores"""
        
        improved_rules = {}
        
        # Analizar patrones de error más comunes
        for error_type, patterns in self.error_patterns.items():
            if len(patterns) >= 2:  # Solo reglas con al menos 2 ejemplos
                
                # Encontrar palabras clave más comunes en este tipo de error
                all_keywords = []
                for pattern in patterns:
                    all_keywords.extend(pattern['keywords'])
                
                keyword_counts = Counter(all_keywords)
                common_keywords = [kw for kw, count in keyword_counts.most_common(5)]
                
                # Crear regla mejorada
                rule_key = '_'.join(common_keywords[:3])
                
                if patterns:
                    expected_hs = patterns[0]['expected_hs']
                    improved_rules[rule_key] = {
                        'hs6': expected_hs[:6],
                        'national_code': expected_hs,
                        'title': f'Regla aprendida para {error_type}',
                        'keywords': common_keywords,
                        'confidence': min(0.95, 0.7 + len(patterns) * 0.05)
                    }
        
        return improved_rules
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Genera insights del sistema de aprendizaje"""
        
        total_errors = sum(len(patterns) for patterns in self.error_patterns.values())
        total_successes = sum(len(patterns) for patterns in self.success_patterns.values())
        
        # Errores más comunes
        common_errors = []
        for error_type, patterns in self.error_patterns.items():
            common_errors.append({
                'error_type': error_type,
                'count': len(patterns),
                'percentage': len(patterns) / total_errors * 100 if total_errors > 0 else 0
            })
        
        common_errors.sort(key=lambda x: x['count'], reverse=True)
        
        # Categorías más problemáticas
        problematic_categories = []
        for error_type, patterns in self.error_patterns.items():
            if len(patterns) >= 3:
                problematic_categories.append({
                    'category': error_type,
                    'error_count': len(patterns),
                    'suggested_improvements': self._suggest_improvements(error_type, patterns)
                })
        
        return {
            'total_errors': total_errors,
            'total_successes': total_successes,
            'accuracy': total_successes / (total_successes + total_errors) * 100 if (total_successes + total_errors) > 0 else 0,
            'common_errors': common_errors[:10],
            'problematic_categories': problematic_categories,
            'learned_rules_count': len(self.learned_rules),
            'improvement_suggestions': self._generate_improvement_suggestions()
        }
    
    def _suggest_improvements(self, error_type: str, patterns: List[Dict]) -> List[str]:
        """Sugiere mejoras específicas para un tipo de error"""
        suggestions = []
        
        if 'wrong_chapter' in error_type:
            suggestions.append("Agregar sinónimos específicos para términos técnicos")
            suggestions.append("Mejorar detección de categorías de productos")
        
        if len(patterns) >= 5:
            suggestions.append("Crear regla específica para este tipo de producto")
            suggestions.append("Expandir base de datos con más ejemplos similares")
        
        return suggestions
    
    def _generate_improvement_suggestions(self) -> List[str]:
        """Genera sugerencias generales de mejora"""
        suggestions = []
        
        if len(self.error_patterns) > 0:
            suggestions.append("Implementar más reglas específicas para productos técnicos")
            suggestions.append("Expandir diccionario de sinónimos")
            suggestions.append("Mejorar detección de categorías de productos")
            suggestions.append("Agregar más ejemplos a la base de datos")
        
        return suggestions
    
    def save_learning_data(self, filepath: str):
        """Guarda los datos de aprendizaje en un archivo"""
        data = {
            'error_patterns': dict(self.error_patterns),
            'success_patterns': dict(self.success_patterns),
            'learned_rules': self.learned_rules,
            'insights': self.get_learning_insights()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_learning_data(self, filepath: str):
        """Carga los datos de aprendizaje desde un archivo"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.error_patterns = defaultdict(list, data.get('error_patterns', {}))
            self.success_patterns = defaultdict(list, data.get('success_patterns', {}))
            self.learned_rules = data.get('learned_rules', {})
            
        except FileNotFoundError:
            logging.info("Archivo de datos de aprendizaje no encontrado, iniciando desde cero")
        except Exception as e:
            logging.error(f"Error cargando datos de aprendizaje: {e}")
