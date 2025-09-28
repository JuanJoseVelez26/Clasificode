from functools import wraps
from flask import request, jsonify
from servicios.token_service import TokenService
from passlib.hash import bcrypt
import jwt
import json

token_service = TokenService()

def hash_password(password: str) -> str:
    """Hashear contraseña usando bcrypt"""
    return bcrypt.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verificar contraseña contra hash bcrypt"""
    return bcrypt.verify(password, hashed_password)

def require_auth(f):
    """Decorador para requerir autenticación JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Obtener token del header Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'code': 401,
                    'message': 'Token de autenticación requerido',
                    'details': 'Se requiere el header Authorization con el token JWT'
                }), 401
            
            # Extraer token (formato: "Bearer <token>")
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    'code': 401,
                    'message': 'Formato de token inválido',
                    'details': 'El token debe tener el formato: Bearer <token>'
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Validar token
            payload = token_service.validate_token(token)
            if not payload:
                return jsonify({
                    'code': 401,
                    'message': 'Token inválido o expirado',
                    'details': 'El token proporcionado no es válido o ha expirado'
                }), 401
            
            # Agregar información del usuario al request
            request.user_id = payload.get('user_id')
            request.user_email = payload.get('email')
            request.user_role = payload.get('role')
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'code': 401,
                'message': 'Token expirado',
                'details': 'El token de autenticación ha expirado'
            }), 401
            
        except jwt.InvalidTokenError:
            return jsonify({
                'code': 401,
                'message': 'Token inválido',
                'details': 'El token de autenticación no es válido'
            }), 401
            
        except Exception as e:
            return jsonify({
                'code': 500,
                'message': 'Error en autenticación',
                'details': str(e)
            }), 500
    
    return decorated_function

def require_role(required_role: str):
    """Decorador para requerir un rol específico"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Asumimos que @require_auth ya corrió y pobló request.user_role
            user_role = getattr(request, 'user_role', None)
            if not user_role:
                return jsonify({
                    'code': 401,
                    'message': 'No autenticado',
                    'details': 'Token no presente o inválido'
                }), 401
            
            # Verificar si el rol es suficiente
            if not has_permission(user_role, required_role):
                return jsonify({
                    'code': 403,
                    'message': 'Permisos insuficientes',
                    'details': f'Se requiere rol {required_role} o superior. Rol actual: {user_role}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_admin(f):
    """Decorador para requerir rol de administrador"""
    return require_role('admin')(f)

def require_auditor(f):
    """Decorador para requerir rol de auditor o superior"""
    return require_role('auditor')(f)

def require_operator(f):
    """Decorador para requerir rol de operador o superior"""
    return require_role('operator')(f)

def has_permission(user_role: str, required_role: str) -> bool:
    """Verificar si un rol tiene permisos para realizar una acción"""
    role_hierarchy = {
        'admin': 3,
        'auditor': 2,
        'operator': 1
    }
    
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level

def get_current_user():
    """Obtener información del usuario actual"""
    if hasattr(request, 'user_id'):
        return {
            'user_id': request.user_id,
            'email': request.user_email,
            'role': request.user_role
        }
    return None

def is_admin():
    """Verificar si el usuario actual es administrador"""
    user = get_current_user()
    return user and user.get('role') == 'admin'

def is_auditor():
    """Verificar si el usuario actual es auditor o superior"""
    user = get_current_user()
    return user and has_permission(user.get('role'), 'auditor')

def is_operator():
    """Verificar si el usuario actual es operador o superior"""
    user = get_current_user()
    return user and has_permission(user.get('role'), 'operator')

def generate_password_hash(password: str) -> str:
    """Generar hash de contraseña (alias para compatibilidad)"""
    return hash_password(password)

def check_password_hash(hashed_password: str, password: str) -> bool:
    """Verificar hash de contraseña (alias para compatibilidad)"""
    return verify_password(password, hashed_password)

# Configuración de seguridad
SECURITY_CONFIG = {
    'password_min_length': 8,
    'password_require_uppercase': True,
    'password_require_lowercase': True,
    'password_require_digits': True,
    'password_require_special': True,
    'max_login_attempts': 5,
    'lockout_duration_minutes': 30,
    'session_timeout_minutes': 60,
    'jwt_expiration_hours': 24
}

def validate_password_strength(password: str) -> dict:
    """Validar fortaleza de contraseña"""
    errors = []
    
    if len(password) < SECURITY_CONFIG['password_min_length']:
        errors.append(f"La contraseña debe tener al menos {SECURITY_CONFIG['password_min_length']} caracteres")
    
    if SECURITY_CONFIG['password_require_uppercase'] and not any(c.isupper() for c in password):
        errors.append("La contraseña debe contener al menos una letra mayúscula")
    
    if SECURITY_CONFIG['password_require_lowercase'] and not any(c.islower() for c in password):
        errors.append("La contraseña debe contener al menos una letra minúscula")
    
    if SECURITY_CONFIG['password_require_digits'] and not any(c.isdigit() for c in password):
        errors.append("La contraseña debe contener al menos un dígito")
    
    if SECURITY_CONFIG['password_require_special'] and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        errors.append("La contraseña debe contener al menos un carácter especial")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'strength': calculate_password_strength(password)
    }

def calculate_password_strength(password: str) -> str:
    """Calcular fortaleza de contraseña"""
    score = 0
    
    # Longitud
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    
    # Complejidad
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        score += 1
    
    # Variedad de caracteres
    unique_chars = len(set(password))
    if unique_chars >= len(password) * 0.7:
        score += 1
    
    if score <= 2:
        return 'weak'
    elif score <= 4:
        return 'medium'
    elif score <= 6:
        return 'strong'
    else:
        return 'very_strong'

def sanitize_input(text: str) -> str:
    """Sanitizar entrada de texto para prevenir inyecciones"""
    if not text:
        return ""
    
    # Remover caracteres peligrosos
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
    sanitized = text
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Limitar longitud
    max_length = 10000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()

def validate_email(email: str) -> bool:
    """Validar formato de email"""
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def rate_limit_check(user_id: int, action: str, limit: int = 10, window_minutes: int = 1) -> bool:
    """Verificar límite de tasa para una acción (implementación básica)"""
    # En producción, esto debería usar Redis o similar
    # Por ahora, retornamos True (sin límite)
    return True

def log_security_event(event_type: str, user_id: int = None, details: dict = None):
    """Registrar evento de seguridad"""
    # En producción, esto debería escribir a un log de seguridad
    event = {
        'timestamp': None,
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': request.remote_addr if request else None,
        'user_agent': request.headers.get('User-Agent') if request else None,
        'details': details or {}
    }
    
    from datetime import datetime
    event['timestamp'] = datetime.now().isoformat()
    
    # Por ahora, solo imprimir (en producción sería logging)
    print(f"SECURITY_EVENT: {json.dumps(event)}")
    
    return event
