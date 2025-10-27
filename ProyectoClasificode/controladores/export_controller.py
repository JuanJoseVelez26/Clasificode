#!/usr/bin/env python3
"""
Controlador para exportación de resultados de clasificación
"""

import csv
import io
import json
from datetime import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, send_file, Response
from werkzeug.exceptions import BadRequest

bp = Blueprint('export', __name__, url_prefix='/export')

def generate_pdf_report(classification_data: Dict[str, Any]) -> bytes:
    """Genera un reporte PDF de la clasificación (HTML que se puede convertir a PDF)"""
    
    # Generar HTML directamente sin Jinja2
    hs_code = classification_data.get('hs_code', 'N/A')
    description = classification_data.get('description', 'N/A')
    confidence_percent = round(classification_data.get('confidence', 0) * 100)
    product_description = classification_data.get('product_description', 'N/A')
    input_type = classification_data.get('input_type', 'text')
    classification_date = classification_data.get('classification_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    explanation = classification_data.get('explanation', '')
    similar_items = classification_data.get('similar_items', [])
    generation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Generar HTML directamente
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte de Clasificación Arancelaria - Clasificode</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #2563eb; padding-bottom: 20px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #2563eb; }}
            .subtitle {{ color: #6b7280; font-size: 16px; }}
            .classification-result {{ background: #f0f9ff; border: 2px solid #2563eb; border-radius: 10px; padding: 30px; text-align: center; margin: 30px 0; }}
            .hs-code {{ font-size: 48px; font-weight: bold; color: #2563eb; margin: 20px 0; }}
            .description {{ font-size: 18px; color: #374151; margin: 15px 0; }}
            .confidence {{ background: #10b981; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-top: 15px; display: inline-block; }}
            .details-section {{ margin: 30px 0; padding: 20px; background: #f9fafb; border-radius: 10px; border-left: 4px solid #2563eb; }}
            .details-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 15px; }}
            .detail-row {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }}
            .detail-label {{ font-weight: 600; color: #4b5563; }}
            .detail-value {{ color: #1f2937; }}
            .explanation {{ background: #fef3c7; border: 1px solid #f59e0b; border-radius: 10px; padding: 20px; margin: 20px 0; }}
            .explanation-title {{ font-weight: bold; color: #92400e; margin-bottom: 10px; }}
            .explanation-text {{ color: #78350f; line-height: 1.6; }}
            .footer {{ margin-top: 40px; text-align: center; color: #6b7280; font-size: 12px; border-top: 1px solid #e5e7eb; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">Clasificode</div>
            <div class="subtitle">Sistema de Clasificación Arancelaria Inteligente</div>
        </div>

        <div class="classification-result">
            <h2>Resultado de Clasificación</h2>
            <div class="hs-code">{hs_code}</div>
            <div class="description">{description}</div>
            <div class="confidence">Confianza: {confidence_percent}%</div>
        </div>

        <div class="details-section">
            <div class="details-title">Detalles de la Clasificación</div>
            
            <div class="detail-row">
                <span class="detail-label">Código HS:</span>
                <span class="detail-value">{hs_code}</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Descripción:</span>
                <span class="detail-value">{description}</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Confianza:</span>
                <span class="detail-value">{confidence_percent}%</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Producto Analizado:</span>
                <span class="detail-value">{product_description}</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Tipo de Entrada:</span>
                <span class="detail-value">{input_type}</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Fecha de Clasificación:</span>
                <span class="detail-value">{classification_date}</span>
            </div>
        </div>
    """
    
    # Agregar explicación si existe
    if explanation:
        html_content += f"""
        <div class="explanation">
            <div class="explanation-title">Explicación de la Clasificación</div>
            <div class="explanation-text">{explanation}</div>
        </div>
        """
    
    # Agregar productos similares si existen
    if similar_items:
        html_content += """
        <div class="details-section">
            <div class="details-title">Productos Similares</div>
        """
        for item in similar_items[:5]:
            html_content += f"""
            <div class="detail-row">
                <span class="detail-label">{item.get('hs_code', 'N/A')}:</span>
                <span class="detail-value">{item.get('description', 'N/A')}</span>
            </div>
            """
        html_content += "</div>"
    
    # Footer
    html_content += f"""
        <div class="footer">
            <div>Reporte generado por Clasificode</div>
            <div>Generado el {generation_date}</div>
        </div>
    </body>
    </html>
    """
    
    return html_content.encode('utf-8')

def generate_simple_pdf(classification_data: Dict[str, Any]) -> bytes:
    """Genera un PDF simple sin dependencias externas"""
    # Por ahora, devolver un HTML que se puede convertir a PDF
    html_content = f"""
    <html>
    <head>
        <title>Reporte de Clasificación</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .hs-code {{ font-size: 36px; font-weight: bold; color: #2563eb; }}
            .details {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Clasificode - Reporte de Clasificación</h1>
        </div>
        <div class="hs-code">{classification_data.get('hs_code', 'N/A')}</div>
        <div class="details">
            <p><strong>Descripción:</strong> {classification_data.get('description', 'N/A')}</p>
            <p><strong>Confianza:</strong> {round(classification_data.get('confidence', 0) * 100)}%</p>
            <p><strong>Producto:</strong> {classification_data.get('product_description', 'N/A')}</p>
            <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    return html_content.encode('utf-8')

def generate_csv_report(classification_data: Dict[str, Any]) -> str:
    """Genera un reporte CSV de la clasificación"""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados
    writer.writerow([
        'Código HS',
        'Descripción',
        'Confianza (%)',
        'Producto Analizado',
        'Tipo de Entrada',
        'Fecha de Clasificación',
        'Explicación',
        'Productos Similares'
    ])
    
    # Datos principales
    similar_items_str = '; '.join([
        f"{item.get('hs_code', '')}: {item.get('description', '')}"
        for item in classification_data.get('similar_items', [])[:5]
    ])
    
    writer.writerow([
        classification_data.get('hs_code', 'N/A'),
        classification_data.get('description', 'N/A'),
        round(classification_data.get('confidence', 0) * 100),
        classification_data.get('product_description', 'N/A'),
        classification_data.get('input_type', 'text'),
        classification_data.get('classification_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        classification_data.get('explanation', ''),
        similar_items_str
    ])
    
    # Si hay múltiples clasificaciones (topK), agregarlas
    if 'top_k' in classification_data:
        writer.writerow([])  # Línea vacía
        writer.writerow(['Clasificaciones Alternativas'])
        writer.writerow(['Código HS', 'Descripción', 'Confianza (%)'])
        
        for item in classification_data['top_k']:
            writer.writerow([
                item.get('hs_code', 'N/A'),
                item.get('description', 'N/A'),
                round(item.get('confidence', 0) * 100)
            ])
    
    return output.getvalue()

@bp.route('/pdf', methods=['POST'])
def export_pdf():
    """Endpoint para exportar clasificación a PDF (HTML que se puede imprimir a PDF)"""
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest('Datos de clasificación requeridos')
        
        # Generar HTML (que se puede convertir a PDF desde el navegador)
        html_content = generate_pdf_report(data)
        
        # Crear respuesta
        filename = f"clasificacion_{data.get('hs_code', 'resultado')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'text/html; charset=utf-8'
            }
        )
        
    except Exception as e:
        return jsonify({
            'error': 'Error generando reporte',
            'message': str(e)
        }), 500

@bp.route('/csv', methods=['POST'])
def export_csv():
    """Endpoint para exportar clasificación a CSV"""
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest('Datos de clasificación requeridos')
        
        # Generar CSV
        csv_content = generate_csv_report(data)
        
        # Crear respuesta
        filename = f"clasificacion_{data.get('hs_code', 'resultado')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        return jsonify({
            'error': 'Error generando CSV',
            'message': str(e)
        }), 500

@bp.route('/formats', methods=['GET'])
def get_export_formats():
    """Obtiene los formatos de exportación disponibles"""
    return jsonify({
        'formats': [
            {
                'format': 'pdf',
                'name': 'PDF',
                'description': 'Reporte completo en formato PDF',
                'icon': 'file-pdf'
            },
            {
                'format': 'csv',
                'name': 'CSV',
                'description': 'Datos en formato CSV para análisis',
                'icon': 'file-csv'
            }
        ]
    })
