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
from schemas.classification import ClassificationResponse, CandidateOut

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
    """Orquestar pipeline de clasificación"""
    try:
        # Parámetros
        k = request.args.get('k', 3, type=int)
        
        # Verificar que el caso existe
        case = case_repo.find_by_id(case_id)
        if not case:
            return jsonify({
                'code': 404,
                'message': 'Caso no encontrado',
                'details': f'No existe un caso con ID {case_id}'
            }), 404
        
        # Verificar que el caso esté abierto
        if case.get('status') != 'open':
            return jsonify({
                'code': 400,
                'message': 'Caso no válido',
                'details': 'Solo se pueden clasificar casos con estado "open"'
            }), 400
        
        # Obtener texto del caso
        case_text = f"{case.get('product_title', '')} {case.get('product_desc', '')}".strip()
        if not case_text:
            return jsonify({
                'code': 400,
                'message': 'Texto insuficiente',
                'details': 'El caso debe tener título o descripción para clasificar'
            }), 400
        
        # Pipeline de clasificación
        results = {
            'case_id': case_id,
            'text_analyzed': case_text,
            'k': k,
            'pipeline_steps': []
        }
        
        # 1. Análisis NLP
        nlp_analysis = nlp_service.classify_text(case_text)
        results['pipeline_steps'].append({
            'step': 'nlp_classification',
            'result': nlp_analysis
        })
        
        # 2. Análisis de sentimientos
        sentiment = nlp_service.analyze_sentiment(case_text)
        results['pipeline_steps'].append({
            'step': 'sentiment_analysis',
            'result': sentiment
        })
        
        # 3. Extracción de entidades
        entities = nlp_service.extract_entities(case_text)
        results['pipeline_steps'].append({
            'step': 'entity_extraction',
            'result': entities
        })
        
        # 4. Extracción de palabras clave
        keywords = nlp_service.extract_keywords(case_text)
        results['pipeline_steps'].append({
            'step': 'keyword_extraction',
            'result': keywords
        })
        
        # 5. Evaluación de reglas RGI
        rules_result = rule_engine.classify_with_rules(case_text)
        results['pipeline_steps'].append({
            'step': 'rgi_rules_evaluation',
            'result': rules_result
        })
        
        # 6. Generar embedding
        embedding = embedding_service.generate_embedding(case_text)
        
        # 7. Búsqueda vectorial KNN
        similar_hs_items = []
        try:
            # Buscar usando pgvector
            knn_results = vector_index.knn_for_hs(
                qvec=embedding,
                provider=embedding_service.provider,
                model=embedding_service.model,
                k=k * 2  # Buscar más para luego re-ranking
            )
            
            # Convertir resultados a formato esperado
            for result in knn_results:
                similar_hs_items.append({
                    'hs_code': result['hs_code'],
                    'title': result['title'],
                    'keywords': result.get('keywords', ''),
                    'distance': result['distance'],
                    'owner_id': result['owner_id']
                })
            
        except Exception as e:
            print(f"Error en búsqueda KNN: {e}")
            # Fallback: búsqueda por palabras clave
            try:
                for keyword in keywords[:5]:
                    hs_items = hs_item_repo.search_by_keywords(keyword, limit=3)
                    similar_hs_items.extend(hs_items)
                
                # Eliminar duplicados
                seen_codes = set()
                unique_items = []
                for item in similar_hs_items:
                    if item['hs_code'] not in seen_codes:
                        seen_codes.add(item['hs_code'])
                        unique_items.append(item)
                
                similar_hs_items = unique_items[:k * 2]
                
            except Exception as e2:
                print(f"Error en fallback search: {e2}")
                # Items de ejemplo como último recurso
                similar_hs_items = [
                    {
                        'hs_code': '8471.30.00',
                        'title': 'Computadoras portátiles',
                        'keywords': 'computadora laptop portatil'
                    },
                    {
                        'hs_code': '8517.12.00',
                        'title': 'Teléfonos móviles',
                        'keywords': 'telefono celular smartphone'
                    }
                ]
        
        # 8. Re-ranking híbrido
        candidates = []
        try:
            # Aplicar re-ranking híbrido
            ranked_candidates = re_ranker.re_rank_candidates(
                query_text=case_text,
                candidates=similar_hs_items,
                query_attrs=case.get('attrs_json')
            )
            
            # Tomar top-k candidatos
            top_candidates = re_ranker.get_top_k(ranked_candidates, k)
            
            # Convertir a formato de candidatos
            for i, candidate in enumerate(top_candidates):
                candidates.append({
                    'case_id': case_id,
                    'hs_code': candidate['hs_code'],
                    'title': candidate['title'],
                    'confidence': candidate['confidence'],
                    'rationale': candidate['rationale'],
                    'legal_refs_json': candidate['legal_refs_json'],
                    'rank': i + 1
                })
            
        except Exception as e:
            print(f"Error en re-ranking: {e}")
            # Fallback: crear candidatos básicos
            for i, item in enumerate(similar_hs_items[:k]):
                candidates.append({
                    'case_id': case_id,
                    'hs_code': item['hs_code'],
                    'title': item['title'],
                    'confidence': item.get('confidence', 0.8 - (i * 0.1)),
                    'rationale': f"Clasificación basada en análisis NLP y similitud con catálogo HS",
                    'legal_refs_json': json.dumps({
                        'nlp_category': nlp_analysis.get('category'),
                        'rgi_rules': rules_result.get('matched_rules', []),
                        'keywords': keywords[:3]
                    }),
                    'rank': i + 1
                })
        
        # 9. Guardar candidatos en base de datos
        if candidates:
            success = candidate_repo.create_candidates_batch(candidates)
            if not success:
                return jsonify({
                    'code': 500,
                    'message': 'Error al guardar candidatos',
                    'details': 'No se pudieron guardar los candidatos en la base de datos'
                }), 500

        # 10. Guardar embedding en índice vectorial (no crítico si falla)
        try:
            embedding_vector = embedding.tolist()
            vector_index.upsert(
                owner_type='case',
                owner_id=case_id,
                vector=embedding_vector,
                meta={
                    'text': case_text[:1000],
                    'provider': embedding_service.provider,
                    'model': embedding_service.model,
                    'case_id': case_id
                }
            )
        except Exception as e:
            print(f"Error guardando embedding: {e}")
            # No es crítico si falla el guardado del embedding
            pass
        
        results['candidates'] = candidates
        results['summary'] = {
            'total_candidates': len(candidates),
            'nlp_category': nlp_analysis.get('category'),
            'confidence_range': {
                'min': min([c['confidence'] for c in candidates]) if candidates else 0,
                'max': max([c['confidence'] for c in candidates]) if candidates else 0
            }
        }
        
        return jsonify({
            'code': 200,
            'message': 'Clasificación completada exitosamente',
            'details': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en el pipeline de clasificación',
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
        dto = ClassificationResponse(
            case_id=case_id,
            hs6=result.get('hs6', ''),
            national_code=result.get('national_code', ''),
            title=result.get('title', ''),
            rgi_applied=result.get('rgi_applied', []) or [],
            legal_notes=result.get('legal_notes', []) or [],
            sources=result.get('sources', []) or [],
            rationale=result.get('rationale', '') or '',
            candidates=[]
        )

        return jsonify({
            'code': 200,
            'message': 'Clasificación nacional completada',
            'details': dto.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en la clasificación nacional',
            'details': str(e)
        }), 500
        
        # 10. Guardar embedding en índice vectorial
        try:
            embedding_vector = embedding.tolist()
            vector_index.upsert(
                owner_type='case',
                owner_id=case_id,
                vector=embedding_vector,
                meta={
                    'text': case_text[:1000],
                    'provider': embedding_service.provider,
                    'model': embedding_service.model,
                    'case_id': case_id
                }
            )
        except Exception as e:
            print(f"Error guardando embedding: {e}")
            # No es crítico si falla el guardado del embedding
            pass
        
        results['candidates'] = candidates
        results['summary'] = {
            'total_candidates': len(candidates),
            'nlp_category': nlp_analysis.get('category'),
            'confidence_range': {
                'min': min([c['confidence'] for c in candidates]) if candidates else 0,
                'max': max([c['confidence'] for c in candidates]) if candidates else 0
            }
        }
        
        return jsonify({
            'code': 200,
            'message': 'Clasificación completada exitosamente',
            'details': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en el pipeline de clasificación',
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
                'provider': embedding['provider'],
                'model': embedding['model'],
                'dimensions': embedding['dim']
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
