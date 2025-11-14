from flask import Blueprint, request, jsonify
from servicios.repos import CaseRepository, CandidateRepository, HSItemRepository, EmbeddingRepository
from servicios.modeloPln.nlp_service import NLPService
from servicios.modeloPln.embedding_service import EmbeddingService
from servicios.modeloPln.vector_index import PgVectorIndex
from servicios.agente.rule_engine import RuleEngine
from servicios.agente.re_rank import HybridReRanker
from servicios.security import require_auth
import json
from servicios.classifier import NationalClassifier

bp = Blueprint('classify', __name__)
case_repo = CaseRepository()
candidate_repo = CandidateRepository()
hs_item_repo = HSItemRepository()
embedding_repo = EmbeddingRepository()
nlp_service = NLPService()
embedding_service = EmbeddingService()
vector_index = PgVectorIndex()
rule_engine = RuleEngine()
re_ranker = HybridReRanker()
national_classifier = NationalClassifier()

@bp.route('/classify/<int:case_id>', methods=['POST'])
@require_auth
def classify_case(case_id):
    """Clasifica devolviendo un único código final aplicando RGI y selección nacional.
    Usa NationalClassifier (RGI -> HS6 -> 10 dígitos) y guarda un candidato rank=1.
    """
    try:
        # Verificar que el caso existe
        case = case_repo.find_by_id(case_id)
        if not case:
            return jsonify({
                'code': 404,
                'message': 'Caso no encontrado',
                'details': f'No existe un caso con ID {case_id}'
            }), 404

        if case.get('status') != 'open':
            return jsonify({
                'code': 400,
                'message': 'Caso no válido',
                'details': 'Solo se pueden clasificar casos con estado "open"'
            }), 400

        # Ejecutar clasificador nacional (RGI + selección nacional)
        result = national_classifier.classify(case)

        return jsonify({
            'code': 200,
            'message': 'Clasificación completada',
            'details': {
                'case_id': case_id,
                'hs6': result.get('hs6', ''),
                'national_code': result.get('national_code', ''),
                'hs': result.get('national_code', '') or result.get('hs6', ''),
                'title': result.get('title', ''),
                'confidence': float(result.get('confidence', 0.0) or 0.0),
                'requires_review': bool((result.get('rationale') or {}).get('requires_review', False)),
                'topK': result.get('topK') or result.get('candidates') or [],
                'candidates': result.get('topK') or result.get('candidates') or [],
                'rgi_applied': result.get('rgi_applied', []) or [],
                'legal_notes': result.get('legal_notes', []) or [],
                'sources': result.get('sources', []) or [],
                'rationale': result.get('rationale', {}) or {}
            }
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en clasificación',
            'details': str(e)
        }), 500

# API v1: Clasificación con RGI -> HS6 -> 10 dígitos nacionales
@bp.route('/api/v1/classify/<int:case_id>', methods=['POST'])
@require_auth
def classify_case_v1(case_id):
    """Clasifica un caso hasta código nacional de 10 dígitos usando RGI + vista vigente.
    Respuesta JSON con: case_id, hs6, national_code, title, rgi_applied, legal_notes, sources, rationale
    """
    try:
        case = case_repo.find_by_id(case_id)
        if not case:
            return jsonify({
                'code': 404,
                'message': 'Caso no encontrado',
                'details': f'No existe un caso con ID {case_id}'
            }), 404

        if case.get('status') != 'open':
            return jsonify({
                'code': 400,
                'message': 'Caso no válido',
                'details': 'Solo se pueden clasificar casos con estado "open"'
            }), 400

        result = national_classifier.classify(case)

        # Asegurar respuesta con DTO para campos obligatorios
        rationale = result.get('rationale', {}) or {}
        top_candidates = result.get('topK') or result.get('candidates') or []

        dto = {
            'case_id': case_id,
            'hs6': result.get('hs6', ''),
            'national_code': result.get('national_code', ''),
            'hs': result.get('national_code', '') or result.get('hs6', ''),
            'title': result.get('title', ''),
            'confidence': float(result.get('confidence', 0.0) or 0.0),
            'requires_review': bool(rationale.get('requires_review', False)),
            'topK': top_candidates,
            'candidates': top_candidates,
            'rgi_applied': result.get('rgi_applied', []) or [],
            'legal_notes': result.get('legal_notes', []) or [],
            'sources': result.get('sources', []) or [],
            'rationale': rationale,
        }

        return jsonify({
            'code': 200,
            'message': 'Clasificación nacional completada',
            'details': dto
        }), 200
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en la clasificación nacional',
            'details': str(e)
        }), 500

@bp.route('/explanations/<int:case_id>', methods=['GET'])
@require_auth
def get_explanations(case_id):
    """Obtener explicaciones de clasificación"""
    try:
        # Verificar que el caso existe
        case = case_repo.find_by_id(case_id)
        if not case:
            return jsonify({
                'code': 404,
                'message': 'Caso no encontrado',
                'details': f'No existe un caso con ID {case_id}'
            }), 404
        
        # Obtener candidatos
        candidates = candidate_repo.find_by_case(case_id)
        
        # Obtener embedding si existe
        embedding = embedding_repo.find_by_owner('case', case_id, 'nlp_service', 'custom_v1')
        
        # Generar explicaciones
        explanations = {
            'case_id': case_id,
            'case_text': f"{case.get('product_title', '')} {case.get('product_desc', '')}".strip(),
            'candidates_count': len(candidates),
            'explanations': []
        }
        
        for candidate in candidates:
            legal_refs = json.loads(candidate.get('legal_refs_json', '{}'))
            
            explanation = {
                'hs_code': candidate['hs_code'],
                'title': candidate['title'],
                'confidence': candidate['confidence'],
                'rank': candidate['rank'],
                'rationale': candidate.get('rationale', ''),
                'factors': {
                    'nlp_category': legal_refs.get('nlp_category', 'unknown'),
                    'rgi_rules_applied': legal_refs.get('rgi_rules', []),
                    'keywords_matched': legal_refs.get('keywords', [])
                }
            }
            
            explanations['explanations'].append(explanation)
        
        # Agregar información del embedding si existe
        if embedding:
            explanations['embedding_info'] = {
                'provider': embedding.get('provider'),
                'model': embedding.get('model')
            }
        
        return jsonify({
            'code': 200,
            'message': 'Explicaciones obtenidas exitosamente',
            'details': explanations
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error al obtener explicaciones',
            'details': str(e)
        }), 500

@bp.route('/analyze', methods=['POST'])
@require_auth
def analyze_text():
    """Analizar texto sin clasificar"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'code': 400,
                'message': 'Texto requerido',
                'details': 'Se requiere un JSON con el campo "text"'
            }), 400
        
        text = data['text']
        if not text.strip():
            return jsonify({
                'code': 400,
                'message': 'Texto vacío',
                'details': 'El texto no puede estar vacío'
            }), 400
        
        # Análisis completo
        analysis = {
            'text': text,
            'text_length': len(text),
            'word_count': len(text.split()),
            'analysis': {}
        }
        
        # Clasificación NLP
        classification = nlp_service.classify_text(text)
        analysis['analysis']['classification'] = classification
        
        # Análisis de sentimientos
        sentiment = nlp_service.analyze_sentiment(text)
        analysis['analysis']['sentiment'] = sentiment
        
        # Extracción de entidades
        entities = nlp_service.extract_entities(text)
        analysis['analysis']['entities'] = entities
        
        # Extracción de palabras clave
        keywords = nlp_service.extract_keywords(text)
        analysis['analysis']['keywords'] = keywords
        
        # Evaluación de reglas RGI
        rules_result = rule_engine.classify_with_rules(text)
        analysis['analysis']['rgi_rules'] = rules_result
        
        # Preprocesamiento
        preprocessed = nlp_service.preprocess_text(text)
        analysis['analysis']['preprocessed_text'] = preprocessed
        
        return jsonify({
            'code': 200,
            'message': 'Análisis completado exitosamente',
            'details': analysis
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en el análisis',
            'details': str(e)
        }), 500
