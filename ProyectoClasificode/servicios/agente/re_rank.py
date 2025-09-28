import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from rapidfuzz import fuzz, process
from servicios.modeloPln.embedding_service import EmbeddingService
from servicios.agente.rule_engine import RuleEngine
from servicios.repos import HSItemRepository

class HybridReRanker:
    """Sistema de re-ranking híbrido que combina múltiples scores"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.rule_engine = RuleEngine()
        self.hs_repo = HSItemRepository()
        
        # Pesos para combinar scores
        self.weights = {
            'semantic': 0.4,    # Score semántico (embeddings)
            'lexical': 0.3,     # Score léxico (RapidFuzz)
            'rules': 0.3        # Score de reglas RGI
        }
        
        # Configuración de RapidFuzz
        self.fuzz_config = {
            'scorer': fuzz.token_sort_ratio,  # Token sort ratio para mejor matching
            'score_cutoff': 50,               # Umbral mínimo de similitud
            'limit': 10                       # Límite de resultados
        }
    
    def re_rank_candidates(self, query_text: str, candidates: List[Dict[str, Any]], 
                          query_attrs: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Re-ranking híbrido de candidatos"""
        if not candidates:
            return []
        
        # Generar embedding de la consulta
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Procesar cada candidato
        ranked_candidates = []
        
        for candidate in candidates:
            # Calcular scores individuales
            semantic_score = self._calculate_semantic_score(query_embedding, candidate)
            lexical_score = self._calculate_lexical_score(query_text, candidate)
            rules_score = self._calculate_rules_score(query_text, candidate, query_attrs)
            
            # Combinar scores
            combined_score = self._combine_scores(semantic_score, lexical_score, rules_score)
            
            # Construir rationale
            rationale = self._build_rationale(semantic_score, lexical_score, rules_score, candidate)
            
            # Construir legal_refs_json
            legal_refs = self._build_legal_refs(semantic_score, lexical_score, rules_score, candidate)
            
            # Crear candidato re-rankado
            ranked_candidate = {
                **candidate,
                'confidence': combined_score,
                'scores': {
                    'semantic': semantic_score,
                    'lexical': lexical_score,
                    'rules': rules_score,
                    'combined': combined_score
                },
                'rationale': rationale,
                'legal_refs_json': json.dumps(legal_refs),
                'ranking_timestamp': datetime.now().isoformat()
            }
            
            ranked_candidates.append(ranked_candidate)
        
        # Ordenar por score combinado descendente
        ranked_candidates.sort(key=lambda x: x['scores']['combined'], reverse=True)
        
        return ranked_candidates
    
    def _calculate_semantic_score(self, query_embedding: np.ndarray, candidate: Dict[str, Any]) -> float:
        """Calcular score semántico basado en embeddings"""
        try:
            # Obtener embedding del candidato si está disponible
            if 'embedding' in candidate and candidate['embedding'] is not None:
                candidate_embedding = np.array(candidate['embedding'])
            else:
                # Generar embedding del título del candidato
                candidate_text = f"{candidate.get('title', '')} {candidate.get('keywords', '')}"
                candidate_embedding = self.embedding_service.generate_embedding(candidate_text)
            
            # Calcular similitud coseno
            similarity = self.embedding_service.calculate_similarity(query_embedding, candidate_embedding, 'cosine')
            
            # Convertir distancia a score (1 / (1 + distance))
            score = 1 / (1 + (1 - similarity))
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            print(f"Error calculando score semántico: {e}")
            return 0.0
    
    def _calculate_lexical_score(self, query_text: str, candidate: Dict[str, Any]) -> float:
        """Calcular score léxico usando RapidFuzz"""
        try:
            # Texto del candidato para comparación
            candidate_text = f"{candidate.get('title', '')} {candidate.get('keywords', '')}"
            
            # Calcular similitud usando RapidFuzz
            similarity = fuzz.token_sort_ratio(
                query_text.lower(), 
                candidate_text.lower(),
                score_cutoff=self.fuzz_config['score_cutoff']
            )
            
            # Normalizar a [0, 1]
            score = similarity / 100.0
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            print(f"Error calculando score léxico: {e}")
            return 0.0
    
    def _calculate_rules_score(self, query_text: str, candidate: Dict[str, Any], 
                              query_attrs: Dict[str, Any] = None) -> float:
        """Calcular score basado en reglas RGI"""
        try:
            # Aplicar reglas RGI al texto de consulta
            rules_result = self.rule_engine.apply_rgi_filters(query_text, query_attrs)
            
            # Score base de las reglas aplicadas
            base_score = rules_result.get('final_score', 0.0)
            
            # Bonos adicionales basados en el candidato
            bonus_score = 0.0
            
            # Bono por coincidencia de palabras clave
            candidate_keywords = candidate.get('keywords', '').lower()
            query_words = query_text.lower().split()
            
            keyword_matches = 0
            for word in query_words:
                if len(word) > 3 and word in candidate_keywords:
                    keyword_matches += 1
            
            if keyword_matches > 0:
                bonus_score += min(0.2, keyword_matches * 0.05)
            
            # Bono por nivel de detalle del código HS
            hs_code = candidate.get('hs_code', '')
            if hs_code:
                # Códigos más específicos (más dígitos) reciben bono
                specificity = len(hs_code.replace('.', '').replace('-', ''))
                if specificity >= 8:
                    bonus_score += 0.1
                elif specificity >= 6:
                    bonus_score += 0.05
            
            # Combinar scores
            total_score = base_score + bonus_score
            
            return max(0.0, min(1.0, total_score))
            
        except Exception as e:
            print(f"Error calculando score de reglas: {e}")
            return 0.0
    
    def _combine_scores(self, semantic_score: float, lexical_score: float, rules_score: float) -> float:
        """Combinar scores usando pesos configurados"""
        try:
            combined = (
                semantic_score * self.weights['semantic'] +
                lexical_score * self.weights['lexical'] +
                rules_score * self.weights['rules']
            )
            
            return max(0.0, min(1.0, combined))
            
        except Exception as e:
            print(f"Error combinando scores: {e}")
            return 0.0
    
    def _build_rationale(self, semantic_score: float, lexical_score: float, 
                        rules_score: float, candidate: Dict[str, Any]) -> str:
        """Construir explicación del ranking"""
        rationale_parts = []
        
        # Explicación semántica
        if semantic_score > 0.7:
            rationale_parts.append("Alta similitud semántica con el producto")
        elif semantic_score > 0.4:
            rationale_parts.append("Similitud semántica moderada")
        else:
            rationale_parts.append("Baja similitud semántica")
        
        # Explicación léxica
        if lexical_score > 0.8:
            rationale_parts.append("Coincidencia léxica muy alta")
        elif lexical_score > 0.6:
            rationale_parts.append("Coincidencia léxica alta")
        elif lexical_score > 0.4:
            rationale_parts.append("Coincidencia léxica moderada")
        else:
            rationale_parts.append("Baja coincidencia léxica")
        
        # Explicación de reglas
        if rules_score > 0.6:
            rationale_parts.append("Aplicación favorable de reglas RGI")
        elif rules_score > 0.3:
            rationale_parts.append("Aplicación moderada de reglas RGI")
        else:
            rationale_parts.append("Aplicación limitada de reglas RGI")
        
        # Agregar información del código HS
        hs_code = candidate.get('hs_code', '')
        if hs_code:
            rationale_parts.append(f"Código HS: {hs_code}")
        
        return ". ".join(rationale_parts) + "."
    
    def _build_legal_refs(self, semantic_score: float, lexical_score: float, 
                         rules_score: float, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Construir referencias legales"""
        legal_refs = {
            'semantic_similarity': semantic_score,
            'lexical_similarity': lexical_score,
            'rgi_rules_score': rules_score,
            'hs_code': candidate.get('hs_code'),
            'title': candidate.get('title'),
            'keywords': candidate.get('keywords'),
            'ranking_method': 'hybrid',
            'weights_used': self.weights.copy()
        }
        
        return legal_refs
    
    def adjust_weights(self, new_weights: Dict[str, float]) -> bool:
        """Ajustar pesos del re-ranking"""
        try:
            # Validar que los pesos sumen 1.0
            total_weight = sum(new_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                # Normalizar pesos
                for key in new_weights:
                    new_weights[key] /= total_weight
            
            self.weights.update(new_weights)
            return True
            
        except Exception as e:
            print(f"Error ajustando pesos: {e}")
            return False
    
    def get_ranking_statistics(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Obtener estadísticas del ranking"""
        if not candidates:
            return {}
        
        # Extraer scores
        semantic_scores = [c.get('scores', {}).get('semantic', 0) for c in candidates]
        lexical_scores = [c.get('scores', {}).get('lexical', 0) for c in candidates]
        rules_scores = [c.get('scores', {}).get('rules', 0) for c in candidates]
        combined_scores = [c.get('scores', {}).get('combined', 0) for c in candidates]
        
        return {
            'total_candidates': len(candidates),
            'score_statistics': {
                'semantic': {
                    'mean': np.mean(semantic_scores),
                    'std': np.std(semantic_scores),
                    'min': np.min(semantic_scores),
                    'max': np.max(semantic_scores)
                },
                'lexical': {
                    'mean': np.mean(lexical_scores),
                    'std': np.std(lexical_scores),
                    'min': np.min(lexical_scores),
                    'max': np.max(lexical_scores)
                },
                'rules': {
                    'mean': np.mean(rules_scores),
                    'std': np.std(rules_scores),
                    'min': np.min(rules_scores),
                    'max': np.max(rules_scores)
                },
                'combined': {
                    'mean': np.mean(combined_scores),
                    'std': np.std(combined_scores),
                    'min': np.min(combined_scores),
                    'max': np.max(combined_scores)
                }
            },
            'weights_used': self.weights.copy(),
            'ranking_timestamp': datetime.now().isoformat()
        }
    
    def filter_by_confidence(self, candidates: List[Dict[str, Any]], 
                           min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        """Filtrar candidatos por confianza mínima"""
        return [c for c in candidates if c.get('confidence', 0) >= min_confidence]
    
    def get_top_k(self, candidates: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
        """Obtener top-k candidatos"""
        return candidates[:k]
    
    def analyze_ranking_quality(self, query_text: str, ranked_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizar calidad del ranking"""
        if not ranked_candidates:
            return {'quality_score': 0.0, 'issues': ['No hay candidatos']}
        
        issues = []
        quality_score = 0.0
        
        # Verificar diversidad de scores
        combined_scores = [c.get('scores', {}).get('combined', 0) for c in ranked_candidates]
        score_variance = np.var(combined_scores)
        
        if score_variance < 0.01:
            issues.append("Baja varianza en scores - posible ranking poco discriminativo")
            quality_score -= 0.2
        elif score_variance > 0.25:
            issues.append("Alta varianza en scores - posible ranking muy agresivo")
            quality_score -= 0.1
        
        # Verificar distribución de scores
        semantic_scores = [c.get('scores', {}).get('semantic', 0) for c in ranked_candidates]
        lexical_scores = [c.get('scores', {}).get('lexical', 0) for c in ranked_candidates]
        rules_scores = [c.get('scores', {}).get('rules', 0) for c in ranked_candidates]
        
        # Verificar si algún componente domina demasiado
        score_components = [semantic_scores, lexical_scores, rules_scores]
        component_names = ['semantic', 'lexical', 'rules']
        
        for i, (scores, name) in enumerate(zip(score_components, component_names)):
            if np.mean(scores) > 0.8:
                issues.append(f"Score {name} muy alto - posible sobreponderación")
                quality_score -= 0.1
            elif np.mean(scores) < 0.2:
                issues.append(f"Score {name} muy bajo - posible subponderación")
                quality_score -= 0.1
        
        # Score base
        quality_score += 0.5
        
        # Normalizar a [0, 1]
        quality_score = max(0.0, min(1.0, quality_score))
        
        return {
            'quality_score': quality_score,
            'issues': issues,
            'score_variance': score_variance,
            'component_means': {
                'semantic': np.mean(semantic_scores),
                'lexical': np.mean(lexical_scores),
                'rules': np.mean(rules_scores)
            },
            'analysis_timestamp': datetime.now().isoformat()
        }
