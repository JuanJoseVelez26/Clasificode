import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class RuleEngine:
    """Motor de reglas RGI para clasificación de códigos HS"""
    
    def __init__(self):
        # Reglas RGI con sus patrones y efectos
        self.rgi_rules = {
            'RGI1': {
                'name': 'Regla General de Interpretación 1',
                'description': 'Los títulos de las Secciones, de los Capítulos o de los Subcapítulos solo tienen un valor indicativo',
                'patterns': [
                    r'\b(titulo|seccion|capitulo|subcapitulo)\b',
                    r'\b(valor indicativo|clasificacion preliminar)\b'
                ],
                'effect': 'neutral',
                'weight': 0.1
            },
            'RGI2A': {
                'name': 'Regla General de Interpretación 2A',
                'description': 'Cualquier referencia a un artículo en una partida determinada alcanza al artículo incluso incompleto o sin terminar',
                'patterns': [
                    r'\b(incompleto|sin terminar|parcialmente terminado)\b',
                    r'\b(partida determinada|articulo incompleto)\b'
                ],
                'effect': 'bonus',
                'weight': 0.3
            },
            'RGI2B': {
                'name': 'Regla General de Interpretación 2B',
                'description': 'Cualquier referencia a una materia en una partida determinada alcanza a dicha materia incluso mezclada o asociada',
                'patterns': [
                    r'\b(mezclado|asociado|combinado|mixto)\b',
                    r'\b(materia mezclada|asociacion de materiales)\b'
                ],
                'effect': 'bonus',
                'weight': 0.3
            },
            'RGI3A': {
                'name': 'Regla General de Interpretación 3A',
                'description': 'La partida más específica tendrá prioridad sobre las partidas más genéricas',
                'patterns': [
                    r'\b(especifico|especializado|particular|detallado)\b',
                    r'\b(partida especifica|clasificacion detallada)\b'
                ],
                'effect': 'bonus',
                'weight': 0.4
            },
            'RGI3B': {
                'name': 'Regla General de Interpretación 3B',
                'description': 'Las mezclas y los artículos compuestos de materias diferentes se clasificarán según la materia que les confiera su carácter esencial',
                'patterns': [
                    r'\b(caracter esencial|materia principal|componente principal)\b',
                    r'\b(mezcla|compuesto|material principal)\b'
                ],
                'effect': 'bonus',
                'weight': 0.4
            },
            'RGI3C': {
                'name': 'Regla General de Interpretación 3C',
                'description': 'Cuando no se pueda determinar la materia que confiere el carácter esencial, se aplicará la regla de la partida última',
                'patterns': [
                    r'\b(partida ultima|ultima partida|no determinable)\b',
                    r'\b(caracter no determinable|materia no identificable)\b'
                ],
                'effect': 'neutral',
                'weight': 0.2
            },
            'RGI4': {
                'name': 'Regla General de Interpretación 4',
                'description': 'Los artículos que no puedan clasificarse aplicando las reglas anteriores se clasificarán en la partida de los artículos con los que tengan mayor analogía',
                'patterns': [
                    r'\b(analogia|similar|parecido|semejante)\b',
                    r'\b(mayor analogia|clasificacion por analogia)\b'
                ],
                'effect': 'bonus',
                'weight': 0.3
            },
            'RGI5A': {
                'name': 'Regla General de Interpretación 5A',
                'description': 'Los estuches para cámaras fotográficas, instrumentos musicales, armas, instrumentos de dibujo, collares y continentes similares, especialmente adaptados para contener un artículo determinado',
                'patterns': [
                    r'\b(estuche|caja|contenedor|empaque)\b',
                    r'\b(especialmente adaptado|contenedor especifico)\b'
                ],
                'effect': 'bonus',
                'weight': 0.2
            },
            'RGI5B': {
                'name': 'Regla General de Interpretación 5B',
                'description': 'Los continentes que, además de su función de continente, tengan una utilización durable y presenten las características de artículos de las partidas 96.03 o 96.04',
                'patterns': [
                    r'\b(utilizacion durable|caracteristicas especiales)\b',
                    r'\b(continente durable|uso multiple)\b'
                ],
                'effect': 'bonus',
                'weight': 0.2
            },
            'RGI6': {
                'name': 'Regla General de Interpretación 6',
                'description': 'La clasificación de mercancías en las subpartidas de una misma partida está determinada legalmente por los textos de estas subpartidas',
                'patterns': [
                    r'\b(subpartida|clasificacion legal|texto legal)\b',
                    r'\b(determinacion legal|subpartidas especificas)\b'
                ],
                'effect': 'bonus',
                'weight': 0.5
            }
        }
        
        # Notas específicas del sistema armonizado
        self.hs_notes = {
            'SECTION': {
                'patterns': [
                    r'\b(nota de seccion|seccion especifica)\b',
                    r'\b(exclusion de seccion|alcance seccion)\b'
                ],
                'effect': 'bonus',
                'weight': 0.3
            },
            'CHAPTER': {
                'patterns': [
                    r'\b(nota de capitulo|capitulo especifico)\b',
                    r'\b(exclusion de capitulo|alcance capitulo)\b'
                ],
                'effect': 'bonus',
                'weight': 0.4
            },
            'HEADING': {
                'patterns': [
                    r'\b(nota de partida|partida especifica)\b',
                    r'\b(exclusion de partida|alcance partida)\b'
                ],
                'effect': 'bonus',
                'weight': 0.5
            },
            'SUBHEADING': {
                'patterns': [
                    r'\b(nota de subpartida|subpartida especifica)\b',
                    r'\b(exclusion de subpartida|alcance subpartida)\b'
                ],
                'effect': 'bonus',
                'weight': 0.6
            }
        }
        
        # Palabras clave que indican descartes
        self.discard_keywords = [
            'excluido', 'no incluido', 'no clasifica', 'no aplica',
            'fuera de alcance', 'no corresponde', 'no pertenece',
            'exclusion', 'excepto', 'salvo', 'no comprende'
        ]
        
        # Palabras clave que indican bonos
        self.bonus_keywords = [
            'incluido', 'comprendido', 'clasifica', 'aplica',
            'dentro de alcance', 'corresponde', 'pertenece',
            'inclusion', 'especificamente', 'particularmente'
        ]
    
    def apply_rgi_filters(self, text: str, attrs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Aplicar filtros RGI al texto y atributos"""
        if not text:
            return {
                'matched_rules': [],
                'discards': [],
                'bonuses': [],
                'traces': [],
                'final_score': 0.0
            }
        
        # Normalizar texto
        normalized_text = text.lower()
        
        # Inicializar resultados
        matched_rules = []
        discards = []
        bonuses = []
        traces = []
        
        # Aplicar reglas RGI
        for rule_code, rule in self.rgi_rules.items():
            for pattern in rule['patterns']:
                if re.search(pattern, normalized_text, re.IGNORECASE):
                    matched_rules.append({
                        'rule_code': rule_code,
                        'rule_name': rule['name'],
                        'description': rule['description'],
                        'effect': rule['effect'],
                        'weight': rule['weight'],
                        'matched_pattern': pattern
                    })
                    
                    traces.append({
                        'timestamp': datetime.now().isoformat(),
                        'rule_code': rule_code,
                        'action': f"Regla {rule_code} aplicada",
                        'effect': rule['effect'],
                        'weight': rule['weight']
                    })
                    break
        
        # Aplicar notas del sistema armonizado
        for note_type, note in self.hs_notes.items():
            for pattern in note['patterns']:
                if re.search(pattern, normalized_text, re.IGNORECASE):
                    matched_rules.append({
                        'rule_code': f"NOTE_{note_type}",
                        'rule_name': f"Nota de {note_type.lower()}",
                        'description': f"Nota específica del sistema armonizado para {note_type.lower()}",
                        'effect': note['effect'],
                        'weight': note['weight'],
                        'matched_pattern': pattern
                    })
                    
                    traces.append({
                        'timestamp': datetime.now().isoformat(),
                        'rule_code': f"NOTE_{note_type}",
                        'action': f"Nota {note_type} aplicada",
                        'effect': note['effect'],
                        'weight': note['weight']
                    })
                    break
        
        # Verificar palabras de descarte
        for keyword in self.discard_keywords:
            if keyword in normalized_text:
                discards.append({
                    'keyword': keyword,
                    'reason': f"Palabra clave de descarte encontrada: {keyword}",
                    'weight': -0.5
                })
                
                traces.append({
                    'timestamp': datetime.now().isoformat(),
                    'rule_code': 'DISCARD',
                    'action': f"Descartado por palabra clave: {keyword}",
                    'effect': 'discard',
                    'weight': -0.5
                })
        
        # Verificar palabras de bono
        for keyword in self.bonus_keywords:
            if keyword in normalized_text:
                bonuses.append({
                    'keyword': keyword,
                    'reason': f"Palabra clave de bono encontrada: {keyword}",
                    'weight': 0.3
                })
                
                traces.append({
                    'timestamp': datetime.now().isoformat(),
                    'rule_code': 'BONUS',
                    'action': f"Bono por palabra clave: {keyword}",
                    'effect': 'bonus',
                    'weight': 0.3
                })
        
        # Analizar atributos JSON si están disponibles
        if attrs and isinstance(attrs, dict):
            attr_traces = self._analyze_attributes(attrs)
            traces.extend(attr_traces)
        
        # Calcular score final
        final_score = self._calculate_final_score(matched_rules, discards, bonuses)
        
        return {
            'matched_rules': matched_rules,
            'discards': discards,
            'bonuses': bonuses,
            'traces': traces,
            'final_score': final_score,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _analyze_attributes(self, attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analizar atributos JSON para aplicar reglas adicionales"""
        traces = []
        
        # Verificar material principal
        if 'material' in attrs:
            material = attrs['material'].lower()
            if any(mat in material for mat in ['acero', 'aluminio', 'plastico']):
                traces.append({
                    'timestamp': datetime.now().isoformat(),
                    'rule_code': 'MATERIAL',
                    'action': f"Material identificado: {material}",
                    'effect': 'bonus',
                    'weight': 0.2
                })
        
        # Verificar origen
        if 'origin' in attrs:
            origin = attrs['origin'].lower()
            if origin in ['china', 'usa', 'alemania', 'japon']:
                traces.append({
                    'timestamp': datetime.now().isoformat(),
                    'rule_code': 'ORIGIN',
                    'action': f"Origen identificado: {origin}",
                    'effect': 'bonus',
                    'weight': 0.1
                })
        
        # Verificar uso específico
        if 'use' in attrs:
            use = attrs['use'].lower()
            if any(usage in use for usage in ['industrial', 'medico', 'cientifico']):
                traces.append({
                    'timestamp': datetime.now().isoformat(),
                    'rule_code': 'USE',
                    'action': f"Uso específico identificado: {use}",
                    'effect': 'bonus',
                    'weight': 0.3
                })
        
        return traces
    
    def _calculate_final_score(self, matched_rules: List[Dict], discards: List[Dict], bonuses: List[Dict]) -> float:
        """Calcular score final basado en reglas aplicadas"""
        score = 0.0
        
        # Sumar pesos de reglas aplicadas
        for rule in matched_rules:
            if rule['effect'] == 'bonus':
                score += rule['weight']
            elif rule['effect'] == 'penalty':
                score -= rule['weight']
        
        # Sumar bonos por palabras clave
        for bonus in bonuses:
            score += bonus['weight']
        
        # Restar descartes
        for discard in discards:
            score += discard['weight']  # Ya es negativo
        
        # Normalizar score entre 0 y 1
        score = max(0.0, min(1.0, score))
        
        return score
    
    def classify_with_rules(self, text: str, attrs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Clasificar texto aplicando reglas RGI"""
        result = self.apply_rgi_filters(text, attrs)
        
        # Determinar categoría basada en reglas aplicadas
        category = self._determine_category(result['matched_rules'])
        
        return {
            'category': category,
            'confidence': result['final_score'],
            'rules_applied': len(result['matched_rules']),
            'discards_found': len(result['discards']),
            'bonuses_found': len(result['bonuses']),
            'traces_count': len(result['traces']),
            'details': result
        }
    
    def _determine_category(self, matched_rules: List[Dict]) -> str:
        """Determinar categoría basada en reglas aplicadas"""
        if not matched_rules:
            return 'unknown'
        
        # Contar reglas por tipo
        rule_counts = {}
        for rule in matched_rules:
            rule_type = rule['rule_code'].split('_')[0]
            rule_counts[rule_type] = rule_counts.get(rule_type, 0) + 1
        
        # Determinar categoría dominante
        if 'RGI3' in rule_counts and rule_counts['RGI3'] > 0:
            return 'specific_classification'
        elif 'RGI2' in rule_counts and rule_counts['RGI2'] > 0:
            return 'material_based'
        elif 'RGI4' in rule_counts and rule_counts['RGI4'] > 0:
            return 'analogy_based'
        elif 'NOTE' in rule_counts and rule_counts['NOTE'] > 0:
            return 'note_based'
        else:
            return 'general_classification'
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """Obtener resumen de todas las reglas disponibles"""
        return {
            'total_rules': len(self.rgi_rules),
            'total_notes': len(self.hs_notes),
            'rules': {code: {
                'name': rule['name'],
                'description': rule['description'],
                'effect': rule['effect'],
                'weight': rule['weight']
            } for code, rule in self.rgi_rules.items()},
            'notes': {note_type: {
                'effect': note['effect'],
                'weight': note['weight']
            } for note_type, note in self.hs_notes.items()},
            'discard_keywords': self.discard_keywords,
            'bonus_keywords': self.bonus_keywords
        }
