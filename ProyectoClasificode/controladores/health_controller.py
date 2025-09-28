from flask import Blueprint, jsonify
from servicios.control_conexion import ControlConexion
from datetime import datetime
import os
from servicios.config_loader import load_config

bp = Blueprint('health', __name__)
control_conexion = ControlConexion()

@bp.route('/health', methods=['GET'])
def health_check():
    """Verificación de salud del sistema"""
    try:
        health_status = {
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'environment': {}
        }
        
        # Verificar conexión a base de datos
        try:
            # Intentar ejecutar una consulta simple
            query = "SELECT 1 as health_check"
            df = control_conexion.ejecutar_consulta_sql(query)
            
            if not df.empty:
                health_status['checks']['database'] = {
                    'status': 'ok',
                    'message': 'Conexión a base de datos exitosa',
                    'response_time_ms': 0  # En producción se mediría el tiempo real
                }
            else:
                health_status['checks']['database'] = {
                    'status': 'error',
                    'message': 'Consulta de base de datos no retornó resultados'
                }
                health_status['status'] = 'unhealthy'
                
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'error',
                'message': f'Error de conexión a base de datos: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Verificar servicios críticos
        try:
            # Verificar que los servicios de NLP estén disponibles
            from servicios.modeloPln.nlp_service import NLPService
            nlp_service = NLPService()
            
            # Test simple de clasificación
            test_result = nlp_service.classify_text("test")
            
            health_status['checks']['nlp_service'] = {
                'status': 'ok',
                'message': 'Servicio NLP funcionando correctamente'
            }
            
        except Exception as e:
            health_status['checks']['nlp_service'] = {
                'status': 'error',
                'message': f'Error en servicio NLP: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Verificar servicio de embeddings
        try:
            from servicios.modeloPln.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            
            # Test simple de embedding
            test_embedding = embedding_service.generate_embedding("test")
            
            health_status['checks']['embedding_service'] = {
                'status': 'ok',
                'message': 'Servicio de embeddings funcionando correctamente',
                'embedding_dimensions': len(test_embedding) if hasattr(test_embedding, '__len__') else 'unknown'
            }
            
        except Exception as e:
            health_status['checks']['embedding_service'] = {
                'status': 'error',
                'message': f'Error en servicio de embeddings: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Verificar motor de reglas
        try:
            from servicios.agente.rule_engine import RuleEngine
            rule_engine = RuleEngine()
            
            # Test simple de reglas
            test_rules = rule_engine.classify_with_rules("test")
            
            health_status['checks']['rule_engine'] = {
                'status': 'ok',
                'message': 'Motor de reglas funcionando correctamente'
            }
            
        except Exception as e:
            health_status['checks']['rule_engine'] = {
                'status': 'error',
                'message': f'Error en motor de reglas: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Información del entorno
        health_status['environment'] = {
            'python_version': os.sys.version,
            'platform': os.sys.platform,
            'database_provider': 'PostgreSQL',
            'flask_version': '2.3.3',
            'sqlalchemy_version': '2.0.23'
        }
        
        # Verificar archivos de configuración
        try:
            config = load_config()
            health_status['checks']['configuration'] = {
                'status': 'ok',
                'message': 'Archivo de configuración válido',
                'database_provider': config.get('DatabaseProvider', 'unknown')
            }
        except Exception as e:
            health_status['checks']['configuration'] = {
                'status': 'error',
                'message': f'Error en archivo de configuración: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Verificar repositorios
        try:
            from servicios.repos import CaseRepository, UserRepository, HSItemRepository
            
            # Test simple de repositorios
            case_repo = CaseRepository()
            user_repo = UserRepository()
            hs_repo = HSItemRepository()
            
            health_status['checks']['repositories'] = {
                'status': 'ok',
                'message': 'Repositorios inicializados correctamente'
            }
            
        except Exception as e:
            health_status['checks']['repositories'] = {
                'status': 'error',
                'message': f'Error en repositorios: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Resumen de salud
        total_checks = len(health_status['checks'])
        healthy_checks = sum(1 for check in health_status['checks'].values() if check['status'] == 'ok')
        
        health_status['summary'] = {
            'total_checks': total_checks,
            'healthy_checks': healthy_checks,
            'unhealthy_checks': total_checks - healthy_checks,
            'health_percentage': (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        }
        
        # Determinar código de respuesta HTTP
        http_status = 200 if health_status['status'] == 'healthy' else 503
        
        return jsonify({
            'code': 200,
            'message': 'Verificación de salud completada',
            'details': health_status
        }), http_status
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error crítico en verificación de salud',
            'details': {
                'status': 'critical_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        }), 500

@bp.route('/health/simple', methods=['GET'])
def simple_health_check():
    """Verificación de salud simple (sin autenticación)"""
    try:
        # Verificación básica de conectividad
        query = "SELECT 1 as health_check"
        df = control_conexion.ejecutar_consulta_sql(query)
        
        if not df.empty:
            return jsonify({
                'code': 200,
                'message': 'OK',
                'details': {
                    'status': 'healthy',
                    'database': 'connected',
                    'timestamp': datetime.now().isoformat()
                }
            }), 200
        else:
            return jsonify({
                'code': 503,
                'message': 'Service Unavailable',
                'details': {
                    'status': 'unhealthy',
                    'database': 'disconnected',
                    'timestamp': datetime.now().isoformat()
                }
            }), 503
            
    except Exception as e:
        return jsonify({
            'code': 503,
            'message': 'Service Unavailable',
            'details': {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        }), 503

@bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """Verificación de readiness (listo para recibir tráfico)"""
    try:
        # Verificaciones mínimas para readiness
        checks = {
            'database': False,
            'configuration': False
        }
        
        # Verificar base de datos
        try:
            query = "SELECT 1 as health_check"
            df = control_conexion.ejecutar_consulta_sql(query)
            checks['database'] = not df.empty
        except:
            checks['database'] = False
        
        # Verificar configuración
        try:
            config = load_config()
            checks['configuration'] = 'DatabaseProvider' in config
        except:
            checks['configuration'] = False
        
        # Determinar readiness
        all_ready = all(checks.values())
        
        if all_ready:
            return jsonify({
                'code': 200,
                'message': 'Ready',
                'details': {
                    'status': 'ready',
                    'checks': checks,
                    'timestamp': datetime.now().isoformat()
                }
            }), 200
        else:
            return jsonify({
                'code': 503,
                'message': 'Not Ready',
                'details': {
                    'status': 'not_ready',
                    'checks': checks,
                    'timestamp': datetime.now().isoformat()
                }
            }), 503
            
    except Exception as e:
        return jsonify({
            'code': 503,
            'message': 'Not Ready',
            'details': {
                'status': 'not_ready',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        }), 503

@bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Verificación de liveness (proceso vivo)"""
    try:
        # Verificación básica de que el proceso está vivo
        return jsonify({
            'code': 200,
            'message': 'Alive',
            'details': {
                'status': 'alive',
                'timestamp': datetime.now().isoformat(),
                'pid': os.getpid()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Not Alive',
            'details': {
                'status': 'not_alive',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        }), 500
