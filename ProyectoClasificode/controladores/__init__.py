# Controladores de la aplicación
from .auth_controller import bp as auth_bp
from .cases_controller import bp as cases_bp
from .classify_controller import bp as classify_bp
from .admin_controller import bp as admin_bp
from .health_controller import bp as health_bp

__all__ = [
    'auth_bp',
    'cases_bp', 
    'classify_bp',
    'admin_bp',
    'health_bp'
]
