# app.py (extracto)
# Cargar variables desde .env ANTES de importar controladores (evita que servicios se inicialicen sin env)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from flask import Flask, jsonify
from flask_cors import CORS
from controladores.auth_controller import bp as auth_bp
from controladores.cases_controller import bp as cases_bp
from controladores.classify_controller import bp as classify_bp
from controladores.admin_controller import bp as admin_bp
from controladores.health_controller import bp as health_bp
from controladores.metrics_controller import metrics_bp
from controladores.export_controller import bp as export_bp
import json
from servicios.config_loader import load_config
def create_app():
    """Crear y configurar la aplicación Flask"""
    app = Flask(__name__)
    
    # Configuración de CORS
    CORS(app, 
         origins=['http://localhost:8080', 'http://localhost:3000'],
         supports_credentials=True,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization'])
    
    # Configurar manejo de errores JSON
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'code': 400,
            'message': 'Solicitud incorrecta',
            'details': 'Los datos enviados no son válidos'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'code': 401,
            'message': 'No autorizado',
            'details': 'Se requiere autenticación para acceder a este recurso'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'code': 403,
            'message': 'Acceso prohibido',
            'details': 'No tiene permisos para acceder a este recurso'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'code': 404,
            'message': 'Recurso no encontrado',
            'details': 'La URL solicitada no existe'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'code': 405,
            'message': 'Método no permitido',
            'details': 'El método HTTP utilizado no está permitido para este recurso'
        }), 405
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'code': 500,
            'message': 'Error interno del servidor',
            'details': 'Ha ocurrido un error inesperado'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        return jsonify({
            'code': 500,
            'message': 'Error no manejado',
            'details': str(error)
        }), 500
    
    # Registrar Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(cases_bp, url_prefix='/cases')
    # Registrar classify sin prefijo para respetar rutas existentes '/classify/...'
    # y permitir rutas absolutas '/api/v1/classify/...'
    app.register_blueprint(classify_bp, url_prefix='')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(health_bp, url_prefix='')
    app.register_blueprint(metrics_bp, url_prefix='/metrics')
    app.register_blueprint(export_bp)
    
    # Ruta de prueba sin autenticación
    @app.route('/test-classify', methods=['POST'])
    def test_classify():
        """Ruta de prueba para clasificación sin autenticación"""
        try:
            from servicios.classifier import NationalClassifier
            from flask import request
            
            data = request.get_json()
            if not data or 'text' not in data:
                return jsonify({'error': 'Se requiere campo "text"'}), 400
            
            text = data['text']
            if not text.strip():
                return jsonify({'error': 'El texto no puede estar vacío'}), 400
            
            # Crear clasificador y clasificar
            classifier = NationalClassifier()
            
            # Crear un caso temporal para la clasificación
            case_data = {
                'id': 999,
                'text': text,
                'input_type': 'text'
            }
            
            result = classifier.classify(case_data)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': f'Error en clasificación: {str(e)}'}), 500
    
    # Ruta raíz
    @app.route('/')
    def root():
        return jsonify({
            'code': 200,
            'message': 'API de Clasificación de Códigos HS',
            'details': {
                'version': '1.0.0',
                'endpoints': {
                    'auth': '/auth',
                    'cases': '/cases',
                    'classify': '/classify',
                    'test-classify': '/test-classify',
                    'admin': '/admin',
                    'health': '/health'
                },
                'documentation': 'Consulte la documentación para más detalles'
            }
        }), 200
    
    # Ruta de información de la API
    @app.route('/api/info')
    def api_info():
        return jsonify({
            'code': 200,
            'message': 'Información de la API',
            'details': {
                'name': 'Clasificode API',
                'version': '1.0.0',
                'description': 'API para clasificación automática de códigos HS',
                'database': 'PostgreSQL con pgvector',
                'authentication': 'JWT',
                'cors_origins': ['http://localhost:8080'],
                'endpoints': {
                    'authentication': {
                        'POST /auth/register': 'Registrar nuevo usuario',
                        'POST /auth/login': 'Iniciar sesión',
                        'POST /auth/logout': 'Cerrar sesión',
                        'POST /auth/validate': 'Validar token'
                    },
                    'cases': {
                        'GET /cases': 'Listar casos',
                        'POST /cases': 'Crear caso',
                        'GET /cases/<id>': 'Obtener caso',
                        'POST /cases/<id>/validate': 'Validar caso',
                        'GET /cases/<id>/candidates': 'Obtener candidatos',
                        'POST /cases/<id>/candidates': 'Agregar candidatos'
                    },
                    'classification': {
                        'POST /classify/<case_id>': 'Clasificar caso',
                        'GET /explanations/<case_id>': 'Obtener explicaciones',
                        'POST /analyze': 'Analizar texto'
                    },
                    'administration': {
                        'GET /admin/params': 'Obtener parámetros',
                        'POST /admin/params': 'Actualizar parámetros',
                        'GET /admin/legal-sources': 'Obtener fuentes legales',
                        'POST /admin/legal-sources': 'Agregar fuente legal',
                        'POST /admin/embed-hs': 'Recalcular embeddings HS',
                        'GET /admin/stats': 'Obtener estadísticas',
                        'GET /admin/health': 'Verificación de salud admin'
                    },
                    'health': {
                        'GET /health': 'Verificación de salud completa',
                        'GET /health/simple': 'Verificación simple',
                        'GET /health/ready': 'Verificación de readiness',
                        'GET /health/live': 'Verificación de liveness'
                    },
                    'export': {
                        'POST /export/pdf': 'Exportar clasificación a PDF',
                        'POST /export/csv': 'Exportar clasificación a CSV',
                        'GET /export/formats': 'Obtener formatos disponibles'
                    }
                }
            }
        }), 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Cargar configuración centralizada
    try:
        config = load_config()
        debug_mode = config.get('Debug', False)
        host = config.get('Host', '127.0.0.1')
        port = config.get('Port', 5000)
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        debug_mode = False
        host = '127.0.0.1'
        port = 5000
    
    print(f"Iniciando servidor en http://{host}:{port}")
    print(f"Modo debug: {debug_mode}")
    print(f"CORS habilitado para: http://localhost:8080")
    
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        threaded=True
    )