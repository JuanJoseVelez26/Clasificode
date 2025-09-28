from flask import Blueprint, request, jsonify
from servicios.repos import CaseRepository, CandidateRepository, ValidationRepository, UserRepository
from servicios.security import require_auth, require_role
import json

bp = Blueprint('cases', __name__)
case_repo = CaseRepository()
candidate_repo = CandidateRepository()
validation_repo = ValidationRepository()
user_repo = UserRepository()

@bp.route('/cases', methods=['GET'])
@require_auth
def get_cases():
    """Obtener lista de casos con filtros"""
    try:
        # Parámetros de consulta
        query = request.args.get('query', '')
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '')
        limit = 10
        offset = (page - 1) * limit
        
        # Construir filtros
        filters = {}
        if status:
            filters['status'] = status
        
        # Obtener casos
        if query:
            # Búsqueda por título o descripción
            cases = case_repo.search_cases(query, limit, offset)
        else:
            cases = case_repo.find_all(limit, offset)
        
        # Aplicar filtro de estado si se especifica
        if status:
            cases = [case for case in cases if case.get('status') == status]
        
        return jsonify({
            'code': 200,
            'message': 'Casos obtenidos exitosamente',
            'details': {
                'cases': cases,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': len(cases)
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/cases', methods=['POST'])
@require_auth
def create_case():
    """Crear nuevo caso"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': 'Datos requeridos',
                'details': 'Se requiere un JSON con los datos del caso'
            }), 400
        
        # Validar campos requeridos
        product_title = data.get('product_title')
        if not product_title:
            return jsonify({
                'code': 400,
                'message': 'Título requerido',
                'details': 'product_title es obligatorio'
            }), 400
        
        # Obtener usuario del token
        user_email = request.user
        user = user_repo.find_by_email(user_email)
        if not user:
            return jsonify({
                'code': 401,
                'message': 'Usuario no encontrado',
                'details': 'El usuario del token no existe'
            }), 401
        
        # Preparar datos del caso
        case_data = {
            'created_by': user['id'],
            'status': 'open',
            'product_title': product_title,
            'product_desc': data.get('product_desc', ''),
            'attrs_json': json.dumps(data.get('attrs', {}))
        }
        
        # Crear caso
        case_id = case_repo.create(case_data)
        
        return jsonify({
            'code': 201,
            'message': 'Caso creado exitosamente',
            'details': {
                'case_id': case_id,
                'status': 'open'
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/cases/<int:case_id>', methods=['GET'])
@require_auth
def get_case(case_id):
    """Obtener caso específico"""
    try:
        case = case_repo.find_by_id(case_id)
        if not case:
            return jsonify({
                'code': 404,
                'message': 'Caso no encontrado',
                'details': f'No existe un caso con ID {case_id}'
            }), 404
        
        # Obtener candidatos del caso
        candidates = candidate_repo.find_by_case(case_id)
        
        # Obtener validación si existe
        validation = validation_repo.find_by_case(case_id)
        
        return jsonify({
            'code': 200,
            'message': 'Caso obtenido exitosamente',
            'details': {
                'case': case,
                'candidates': candidates,
                'validation': validation
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/cases/<int:case_id>/validate', methods=['POST'])
@require_auth
@require_role('auditor')
def validate_case(case_id):
    """Validar caso (solo auditores)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': 'Datos requeridos',
                'details': 'Se requiere un JSON con final_hs_code'
            }), 400
        
        final_hs_code = data.get('final_hs_code')
        comment = data.get('comment', '')
        
        if not final_hs_code:
            return jsonify({
                'code': 400,
                'message': 'Código HS requerido',
                'details': 'final_hs_code es obligatorio'
            }), 400
        
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
                'details': 'Solo se pueden validar casos con estado "open"'
            }), 400
        
        # Obtener usuario validador
        user_email = request.user
        user = user_repo.find_by_email(user_email)
        if not user:
            return jsonify({
                'code': 401,
                'message': 'Usuario no encontrado',
                'details': 'El usuario del token no existe'
            }), 401
        
        # Cerrar caso y crear validación
        success = case_repo.close_case(case_id, final_hs_code, user['id'])
        
        if not success:
            return jsonify({
                'code': 500,
                'message': 'Error al validar caso',
                'details': 'No se pudo procesar la validación'
            }), 500
        
        return jsonify({
            'code': 200,
            'message': 'Caso validado exitosamente',
            'details': {
                'case_id': case_id,
                'final_hs_code': final_hs_code,
                'validator_id': user['id'],
                'status': 'validated'
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/cases/<int:case_id>/candidates', methods=['GET'])
@require_auth
def get_case_candidates(case_id):
    """Obtener candidatos de un caso"""
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
        
        return jsonify({
            'code': 200,
            'message': 'Candidatos obtenidos exitosamente',
            'details': {
                'case_id': case_id,
                'candidates': candidates
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/cases/<int:case_id>/candidates', methods=['POST'])
@require_auth
def add_case_candidates(case_id):
    """Agregar candidatos a un caso"""
    try:
        data = request.get_json()
        
        if not data or 'candidates' not in data:
            return jsonify({
                'code': 400,
                'message': 'Candidatos requeridos',
                'details': 'Se requiere un array de candidatos'
            }), 400
        
        candidates = data['candidates']
        if not isinstance(candidates, list):
            return jsonify({
                'code': 400,
                'message': 'Formato inválido',
                'details': 'candidates debe ser un array'
            }), 400
        
        # Verificar que el caso existe
        case = case_repo.find_by_id(case_id)
        if not case:
            return jsonify({
                'code': 404,
                'message': 'Caso no encontrado',
                'details': f'No existe un caso con ID {case_id}'
            }), 404
        
        # Preparar candidatos
        candidates_data = []
        for i, candidate in enumerate(candidates):
            if not candidate.get('hs_code') or not candidate.get('title'):
                return jsonify({
                    'code': 400,
                    'message': 'Datos de candidato incompletos',
                    'details': f'Candidato {i+1} debe tener hs_code y title'
                }), 400
            
            candidates_data.append({
                'case_id': case_id,
                'hs_code': candidate['hs_code'],
                'title': candidate['title'],
                'confidence': candidate.get('confidence', 0.0),
                'rationale': candidate.get('rationale', ''),
                'legal_refs_json': json.dumps(candidate.get('legal_refs', {})),
                'rank': candidate.get('rank', i + 1)
            })
        
        # Crear candidatos en lote
        success = candidate_repo.create_candidates_batch(candidates_data)
        
        if not success:
            return jsonify({
                'code': 500,
                'message': 'Error al crear candidatos',
                'details': 'No se pudieron crear los candidatos'
            }), 500
        
        return jsonify({
            'code': 201,
            'message': 'Candidatos agregados exitosamente',
            'details': {
                'case_id': case_id,
                'candidates_count': len(candidates_data)
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500
