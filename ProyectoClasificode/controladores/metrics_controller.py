"""
Controlador de Métricas del Sistema ClasifiCode

Este módulo implementa endpoints REST para consultar métricas técnicas
del sistema, protegidos por autenticación JWT y solo accesibles para administradores.
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any
import jwt
from servicios.incremental_validation import incremental_validation
from servicios.security import SecurityService
from servicios.metrics_service import metrics_service

# Crear blueprint para métricas
metrics_bp = Blueprint('metrics', __name__)

def admin_required(f):
    """
    Decorador para requerir autenticación de administrador.
    
    Args:
        f: Función a decorar
        
    Returns:
        Función decorada con verificación de admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Obtener token de autorización
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Token de autorización requerido'}), 401
            
            # Extraer token
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            
            # Verificar token
            security_service = SecurityService()
            payload = security_service.verify_token(token)
            
            if not payload:
                return jsonify({'error': 'Token inválido'}), 401
            
            # Verificar que sea administrador
            if not payload.get('is_admin', False):
                return jsonify({'error': 'Acceso denegado: se requiere rol de administrador'}), 403
            
            # Agregar información del usuario a la request
            request.current_user = payload
            
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({'error': f'Error de autenticación: {str(e)}'}), 401
    
    return decorated_function

@metrics_bp.route('/metrics', methods=['GET'])
@admin_required
def get_system_metrics():
    """
    Endpoint para obtener métricas del sistema.
    
    Query Parameters:
        - hours: Número de horas hacia atrás (default: 24)
        - metric: Nombre específico de métrica (opcional)
        
    Returns:
        JSON con métricas del sistema
    """
    try:
        # Obtener parámetros
        hours = int(request.args.get('hours', 24))
        metric_name = request.args.get('metric')
        
        if metric_name:
            # Obtener métrica específica
            trend_data = metrics_service.get_metric_trend(metric_name, hours // 24)
            return jsonify({
                'metric_name': metric_name,
                'trend_data': trend_data,
                'period_hours': hours
            })
        else:
            # Obtener resumen completo
            summary = metrics_service.get_system_health_summary()
            return jsonify(summary)
            
    except ValueError:
        return jsonify({'error': 'Parámetro hours debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error obteniendo métricas: {str(e)}'}), 500

@metrics_bp.route('/metrics/kpis', methods=['GET'])
@admin_required
def get_latest_kpis():
    """
    Endpoint para obtener KPIs más recientes.
    
    Query Parameters:
        - hours: Número de horas hacia atrás (default: 24)
        
    Returns:
        JSON con KPIs más recientes
    """
    try:
        hours = int(request.args.get('hours', 24))
        kpis = metrics_service.get_latest_kpis(hours)
        
        return jsonify({
            'kpis': kpis,
            'period_hours': hours,
            'timestamp': datetime.utcnow().isoformat(),
            'massive_test_summary': metrics_service.get_massive_test_summary()
        })
        
    except ValueError:
        return jsonify({'error': 'Parámetro hours debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error obteniendo KPIs: {str(e)}'}), 500

@metrics_bp.route('/metrics/trend/<metric_name>', methods=['GET'])
@admin_required
def get_metric_trend(metric_name: str):
    """
    Endpoint para obtener tendencia de una métrica específica.
    
    Args:
        metric_name: Nombre de la métrica
        
    Query Parameters:
        - days: Número de días hacia atrás (default: 7)
        
    Returns:
        JSON con datos de tendencia
    """
    try:
        days = int(request.args.get('days', 7))
        trend_data = metrics_service.get_metric_trend(metric_name, days)
        
        return jsonify({
            'metric_name': metric_name,
            'trend_data': trend_data,
            'period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError:
        return jsonify({'error': 'Parámetro days debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error obteniendo tendencia: {str(e)}'}), 500

@metrics_bp.route('/metrics/health', methods=['GET'])
@admin_required
def get_system_health():
    """
    Endpoint para obtener estado de salud del sistema.
    
    Returns:
        JSON con estado de salud del sistema
    """
    try:
        health_summary = metrics_service.get_system_health_summary()
        
        return jsonify(health_summary)
        
    except Exception as e:
        return jsonify({'error': f'Error obteniendo estado de salud: {str(e)}'}), 500

@metrics_bp.route('/metrics/accuracy', methods=['GET'])
@admin_required
def get_accuracy_metrics():
    """
    Endpoint para obtener métricas de precisión del sistema.
    
    Query Parameters:
        - hours: Número de horas hacia atrás (default: 24)
        
    Returns:
        JSON con métricas de precisión
    """
    try:
        hours = int(request.args.get('hours', 24))
        
        # Calcular métricas de precisión
        avg_confidence = metrics_service.calculate_average_confidence(hours)
        feedback_ratio = metrics_service.get_feedback_ratio(hours)
        estimated_accuracy = avg_confidence * (1.0 - feedback_ratio)
        
        return jsonify({
            'estimated_accuracy': estimated_accuracy,
            'average_confidence': avg_confidence,
            'feedback_ratio': feedback_ratio,
            'period_hours': hours,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError:
        return jsonify({'error': 'Parámetro hours debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error obteniendo métricas de precisión: {str(e)}'}), 500

@metrics_bp.route('/metrics/performance', methods=['GET'])
@admin_required
def get_performance_metrics():
    """
    Endpoint para obtener métricas de rendimiento del sistema.
    
    Query Parameters:
        - hours: Número de horas hacia atrás (default: 24)
        
    Returns:
        JSON con métricas de rendimiento
    """
    try:
        hours = int(request.args.get('hours', 24))
        
        # Calcular métricas de rendimiento
        avg_response_time = metrics_service.calculate_average_response_time(hours)
        avg_confidence = metrics_service.calculate_average_confidence(hours)
        
        return jsonify({
            'average_response_time': avg_response_time,
            'average_confidence': avg_confidence,
            'period_hours': hours,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError:
        return jsonify({'error': 'Parámetro hours debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error obteniendo métricas de rendimiento: {str(e)}'}), 500

@metrics_bp.route('/metrics/export', methods=['GET'])
@admin_required
def export_metrics():
    """
    Endpoint para exportar métricas en formato CSV.
    
    Query Parameters:
        - days: Número de días hacia atrás (default: 7)
        - format: Formato de exportación ('csv', 'json') (default: 'csv')
        
    Returns:
        Archivo CSV o JSON con métricas
    """
    try:
        days = int(request.args.get('days', 7))
        export_format = request.args.get('format', 'csv')
        
        # Obtener métricas históricas
        limit_time = datetime.utcnow() - timedelta(days=days)
        
        # Aquí se implementaría la lógica de exportación
        # Por ahora, retornar un mensaje de funcionalidad en desarrollo
        return jsonify({
            'message': 'Funcionalidad de exportación en desarrollo',
            'requested_days': days,
            'requested_format': export_format
        })
        
    except ValueError:
        return jsonify({'error': 'Parámetro days debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error en exportación: {str(e)}'}), 500

@metrics_bp.route('/metrics/incremental', methods=['GET'])
@admin_required
def get_incremental_metrics():
    """
    Endpoint para obtener métricas de validación incremental.
    
    Query Parameters:
        - hours: Número de horas hacia atrás (default: 24)
        
    Returns:
        JSON con métricas de validación incremental
    """
    try:
        hours = int(request.args.get('hours', 24))
        summary = incremental_validation.get_performance_summary(hours)
        
        return jsonify(summary)
        
    except ValueError:
        return jsonify({'error': 'Parámetro hours debe ser un número entero'}), 400
    except Exception as e:
        return jsonify({'error': f'Error obteniendo métricas incrementales: {str(e)}'}), 500

@metrics_bp.route('/metrics/force-kpis', methods=['POST'])
@admin_required
def force_kpi_calculation():
    """
    Endpoint para forzar el cálculo de KPIs con el buffer actual.
    
    Returns:
        JSON con resultado de la operación
    """
    try:
        incremental_validation.force_kpi_calculation()
        
        return jsonify({
            'message': 'Cálculo forzado de KPIs completado',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Error forzando cálculo de KPIs: {str(e)}'}), 500

@metrics_bp.route('/metrics/thresholds', methods=['GET', 'PUT'])
@admin_required
def manage_thresholds():
    """
    Endpoint para consultar o actualizar umbrales de alertas.
    
    GET: Retorna umbrales actuales
    PUT: Actualiza umbrales con datos del body
    
    Returns:
        JSON con umbrales actuales o resultado de actualización
    """
    try:
        if request.method == 'GET':
            return jsonify({
                'thresholds': incremental_validation.thresholds,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        elif request.method == 'PUT':
            new_thresholds = request.get_json()
            if not new_thresholds:
                return jsonify({'error': 'Se requieren datos JSON para actualizar umbrales'}), 400
            
            incremental_validation.update_thresholds(new_thresholds)
            
            return jsonify({
                'message': 'Umbrales actualizados exitosamente',
                'thresholds': incremental_validation.thresholds,
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        return jsonify({'error': f'Error gestionando umbrales: {str(e)}'}), 500
