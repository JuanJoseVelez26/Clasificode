from flask import Blueprint, request, jsonify
from servicios.token_service import TokenService
from servicios.security import hash_password, verify_password
from servicios.repos import UserRepository
import json

bp = Blueprint('auth', __name__)
token_service = TokenService()
user_repo = UserRepository()

@bp.route('/register', methods=['POST'])
def register():
    """Registrar nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        if not data:
            return jsonify({
                'code': 400,
                'message': 'Datos requeridos',
                'details': 'Se requiere un JSON con email, password y name'
            }), 400
        
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not email or not password or not name:
            return jsonify({
                'code': 400,
                'message': 'Campos requeridos',
                'details': 'email, password y name son obligatorios'
            }), 400
        
        # Verificar si el usuario ya existe
        existing_user = user_repo.find_by_email(email)
        if existing_user:
            return jsonify({
                'code': 409,
                'message': 'Usuario ya existe',
                'details': f'El email {email} ya está registrado'
            }), 409
        
        # Hash de la contraseña
        password_hash = hash_password(password)
        
        # Crear usuario (por defecto como operator)
        user_data = {
            'email': email,
            'password_hash': password_hash,
            'name': name,
            'role': 'operator',
            'is_active': True
        }
        
        user_id = user_repo.create(user_data)
        
        return jsonify({
            'code': 201,
            'message': 'Usuario registrado exitosamente',
            'details': {
                'user_id': user_id,
                'email': email,
                'name': name,
                'role': 'operator'
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/login', methods=['POST'])
def login():
    """Iniciar sesión"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': 'Datos requeridos',
                'details': 'Se requiere un JSON con email y password'
            }), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'code': 400,
                'message': 'Campos requeridos',
                'details': 'email y password son obligatorios'
            }), 400
        
        # Buscar usuario
        user = user_repo.find_by_email(email)
        if not user:
            return jsonify({
                'code': 401,
                'message': 'Credenciales inválidas',
                'details': 'Email o contraseña incorrectos'
            }), 401
        
        # Verificar si el usuario está activo
        if not user.get('is_active'):
            return jsonify({
                'code': 401,
                'message': 'Usuario inactivo',
                'details': 'El usuario ha sido desactivado'
            }), 401
        
        # Verificar contraseña
        if not verify_password(password, user['password_hash']):
            return jsonify({
                'code': 401,
                'message': 'Credenciales inválidas',
                'details': 'Email o contraseña incorrectos'
            }), 401
        
        # Generar token JWT
        token = token_service.generar_token(user['email'])
        
        return jsonify({
            'code': 200,
            'message': 'Login exitoso',
            'details': {
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role']
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/logout', methods=['POST'])
def logout():
    """Cerrar sesión (opcional - para blacklist de tokens)"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({
                'code': 400,
                'message': 'Token requerido',
                'details': 'Se requiere el token para cerrar sesión'
            }), 400
        
        token = data['token']
        
        # Aquí podrías implementar blacklist de tokens
        # Por ahora solo validamos que el token sea válido
        payload = token_service.validar_token(token)
        if not payload:
            return jsonify({
                'code': 401,
                'message': 'Token inválido',
                'details': 'El token proporcionado no es válido'
            }), 401
        
        # TODO: Implementar blacklist de tokens
        # token_service.blacklist_token(token)
        
        return jsonify({
            'code': 200,
            'message': 'Logout exitoso',
            'details': 'Sesión cerrada correctamente'
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500

@bp.route('/validate', methods=['POST'])
def validate_token():
    """Validar token JWT"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({
                'code': 400,
                'message': 'Token requerido',
                'details': 'Se requiere el token para validar'
            }), 400
        
        token = data['token']
        payload = token_service.validar_token(token)
        
        if not payload:
            return jsonify({
                'code': 401,
                'message': 'Token inválido',
                'details': 'El token ha expirado o es inválido'
            }), 401
        
        # Buscar información del usuario
        user = user_repo.find_by_email(payload.get('sub'))
        if not user or not user.get('is_active'):
            return jsonify({
                'code': 401,
                'message': 'Usuario no encontrado o inactivo',
                'details': 'El usuario asociado al token no existe o está inactivo'
            }), 401
        
        return jsonify({
            'code': 200,
            'message': 'Token válido',
            'details': {
                'valid': True,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role']
                },
                'payload': payload
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': str(e)
        }), 500
