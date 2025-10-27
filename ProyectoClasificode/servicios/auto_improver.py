#!/usr/bin/env python3
"""
Sistema de mejora automática del clasificador basado en aprendizaje
"""

import json
import os
from typing import Dict, List, Any
from collections import defaultdict, Counter

class AutoImprover:
    def __init__(self, classifier_path: str = "servicios/classifier.py"):
        self.classifier_path = classifier_path
        self.learning_data_path = "learning_data.json"
        
    def load_learning_data(self) -> Dict[str, Any]:
        """Carga los datos de aprendizaje"""
        if os.path.exists(self.learning_data_path):
            with open(self.learning_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def analyze_error_patterns(self, learning_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza los patrones de error para generar mejoras"""
        
        error_patterns = learning_data.get('error_patterns', {})
        insights = learning_data.get('insights', {})
        
        improvements = {
            'new_specific_rules': {},
            'synonym_expansions': {},
            'category_improvements': {},
            'priority_fixes': []
        }
        
        # Analizar errores más comunes
        common_errors = insights.get('common_errors', [])
        
        for error in common_errors:
            error_type = error['error_type']
            count = error['count']
            
            if count >= 2:  # Solo para errores que ocurren al menos 2 veces
                
                if 'wrong_chapter' in error_type:
                    # Error de capítulo incorrecto - necesita regla específica
                    improvements['priority_fixes'].append({
                        'type': 'chapter_error',
                        'error_type': error_type,
                        'count': count,
                        'action': 'add_specific_rule'
                    })
                
                elif 'wrong_subchapter' in error_type:
                    # Error de subcapítulo - necesita sinónimos o regla específica
                    improvements['priority_fixes'].append({
                        'type': 'subchapter_error',
                        'error_type': error_type,
                        'count': count,
                        'action': 'expand_synonyms'
                    })
        
        # Generar reglas específicas basadas en errores
        for error_type, patterns in error_patterns.items():
            if len(patterns) >= 2:
                
                # Extraer palabras clave comunes
                all_keywords = []
                for pattern in patterns:
                    keywords = pattern.get('keywords', [])
                    all_keywords.extend(keywords)
                
                keyword_counts = Counter(all_keywords)
                common_keywords = [kw for kw, count in keyword_counts.most_common(3)]
                
                if common_keywords:
                    rule_key = '_'.join(common_keywords[:2])
                    expected_hs = patterns[0]['expected_hs']
                    
                    improvements['new_specific_rules'][rule_key] = {
                        'hs6': expected_hs[:6],
                        'national_code': expected_hs,
                        'title': f'Regla aprendida para {error_type}',
                        'keywords': common_keywords,
                        'confidence': min(0.95, 0.8 + len(patterns) * 0.05)
                    }
        
        return improvements
    
    def generate_synonym_expansions(self, learning_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Genera expansiones de sinónimos basadas en errores"""
        
        error_patterns = learning_data.get('error_patterns', {})
        synonym_expansions = {}
        
        for error_type, patterns in error_patterns.items():
            if len(patterns) >= 2:
                
                # Extraer palabras clave que causan errores
                all_keywords = []
                for pattern in patterns:
                    keywords = pattern.get('keywords', [])
                    all_keywords.extend(keywords)
                
                keyword_counts = Counter(all_keywords)
                common_keywords = [kw for kw, count in keyword_counts.most_common(5)]
                
                # Generar sinónimos basados en el contexto del error
                for keyword in common_keywords:
                    if keyword not in synonym_expansions:
                        synonym_expansions[keyword] = []
                    
                    # Agregar sinónimos contextuales
                    if 'automovil' in keyword or 'vehiculo' in keyword:
                        synonym_expansions[keyword].extend(['carro', 'auto', 'vehículo', 'turismo'])
                    elif 'electrico' in keyword:
                        synonym_expansions[keyword].extend(['eléctrico', 'electrical', 'powered'])
                    elif 'motocicleta' in keyword:
                        synonym_expansions[keyword].extend(['moto', 'bike', 'motorcycle'])
                    elif 'casco' in keyword:
                        synonym_expansions[keyword].extend(['helmet', 'protección', 'seguridad'])
                    elif 'neumatico' in keyword:
                        synonym_expansions[keyword].extend(['llanta', 'tire', 'rueda'])
                    elif 'freno' in keyword:
                        synonym_expansions[keyword].extend(['brake', 'frenado', 'parada'])
        
        return synonym_expansions
    
    def generate_improvement_report(self) -> str:
        """Genera un reporte de mejoras sugeridas"""
        
        learning_data = self.load_learning_data()
        
        if not learning_data:
            return "No hay datos de aprendizaje disponibles. Ejecute primero el test con aprendizaje."
        
        improvements = self.analyze_error_patterns(learning_data)
        synonym_expansions = self.generate_synonym_expansions(learning_data)
        
        report = []
        report.append("="*80)
        report.append("REPORTE DE MEJORAS SUGERIDAS")
        report.append("="*80)
        
        # Resumen de datos de aprendizaje
        insights = learning_data.get('insights', {})
        report.append(f"Total de errores analizados: {insights.get('total_errors', 0)}")
        report.append(f"Total de éxitos analizados: {insights.get('total_successes', 0)}")
        report.append(f"Precisión actual: {insights.get('accuracy', 0):.2f}%")
        
        # Reglas específicas sugeridas
        if improvements['new_specific_rules']:
            report.append(f"\nREGLAS ESPECÍFICAS SUGERIDAS: {len(improvements['new_specific_rules'])}")
            report.append("-" * 50)
            for rule_key, rule_data in improvements['new_specific_rules'].items():
                report.append(f"- {rule_key}: {rule_data['title']}")
                report.append(f"  HS6: {rule_data['hs6']}, Nacional: {rule_data['national_code']}")
                report.append(f"  Palabras clave: {', '.join(rule_data['keywords'])}")
                report.append("")
        
        # Expansiones de sinónimos sugeridas
        if synonym_expansions:
            report.append(f"\nEXPANSIONES DE SINÓNIMOS SUGERIDAS: {len(synonym_expansions)}")
            report.append("-" * 50)
            for keyword, synonyms in synonym_expansions.items():
                if synonyms:
                    report.append(f"- {keyword}: {', '.join(synonyms)}")
        
        # Prioridades de mejora
        if improvements['priority_fixes']:
            report.append(f"\nPRIORIDADES DE MEJORA:")
            report.append("-" * 50)
            for i, fix in enumerate(improvements['priority_fixes'], 1):
                report.append(f"{i}. {fix['error_type']} ({fix['count']} casos)")
                report.append(f"   Acción sugerida: {fix['action']}")
        
        # Recomendaciones generales
        report.append(f"\nRECOMENDACIONES GENERALES:")
        report.append("-" * 50)
        report.append("1. Implementar las reglas específicas sugeridas")
        report.append("2. Expandir el diccionario de sinónimos")
        report.append("3. Mejorar la detección de categorías de productos")
        report.append("4. Agregar más ejemplos a la base de datos")
        report.append("5. Ejecutar tests periódicos para validar mejoras")
        
        return "\n".join(report)
    
    def apply_improvements(self) -> bool:
        """Aplica las mejoras sugeridas al clasificador"""
        
        learning_data = self.load_learning_data()
        
        if not learning_data:
            print("No hay datos de aprendizaje disponibles.")
            return False
        
        improvements = self.analyze_error_patterns(learning_data)
        
        # Aquí se podrían aplicar las mejoras automáticamente
        # Por ahora, solo generamos el reporte
        
        print("Mejoras analizadas y reporte generado.")
        print("Para aplicar las mejoras, revise el reporte y implemente manualmente.")
        
        return True

def main():
    """Función principal para ejecutar el sistema de mejora automática"""
    
    improver = AutoImprover()
    
    # Generar reporte de mejoras
    report = improver.generate_improvement_report()
    print(report)
    
    # Guardar reporte en archivo
    with open('improvement_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReporte guardado en: improvement_report.txt")

if __name__ == "__main__":
    main()
