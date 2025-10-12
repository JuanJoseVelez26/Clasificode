from flask import Blueprint, request, jsonify
from servicios.repos import HSItemRepository, EmbeddingRepository, RGIRuleRepository, LegalSourceRepository
from servicios.modeloPln.embedding_service import EmbeddingService
from servicios.security import require_auth, require_role
import json
from servicios.scraping.ingestor import DianIngestor
from servicios.control_conexion import ControlConexion

bp = Blueprint('admin', __name__)
hs_item_repo = HSItemRepository()
embedding_repo = EmbeddingRepository()
rgi_rule_repo = RGIRuleRepository()
legal_source_repo = LegalSourceRepository()
embedding_service = EmbeddingService()
cc = ControlConexion()


# Configuración global (en producción esto debería estar en base de datos)
GLOBAL_CONFIG = {
    'k': 3,
    'umbral': 0.7,
    'max_candidates': 10,
    'embedding_model': 'custom_v1',
    'similarity_threshold': 0.8
}

@bp.route('/params', methods=['GET'])
@require_auth
@require_role('admin')
def get_params():
    """Obtener parámetros de configuración"""
    try:
        return jsonify({
            'code': 200,
            'message': 'Parámetros obtenidos exitosamente',
            'details': GLOBAL_CONFIG
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error al obtener parámetros',
            'details': str(e)
        }), 500

@bp.route('/backfill-hs-items', methods=['POST'])
@require_auth
@require_role('admin')
def backfill_hs_items():
    """Puebla hs_items a partir de tariff_items existentes (por HS6). Idempotente."""
    try:
        # Crear/actualizar hs_items agregando por hs6
        sql = (
            "INSERT INTO hs_items (hs_code, title, keywords, level, chapter, created_at, updated_at) "
            "SELECT t.hs6 AS hs_code, MIN(NULLIF(t.title,'')) AS title, "
            "       lower(string_agg(DISTINCT NULLIF(t.title,''), ' ')) AS keywords, "
            "       6 AS level, CAST(SUBSTRING(t.hs6,1,2) AS integer) AS chapter, NOW(), NOW() "
            "FROM tariff_items t GROUP BY t.hs6 "
            "ON CONFLICT (hs_code) DO UPDATE SET "
            "  title = COALESCE(EXCLUDED.title, hs_items.title), "
            "  keywords = CONCAT(COALESCE(hs_items.keywords,''),' ',COALESCE(EXCLUDED.keywords,'')), "
            "  chapter = COALESCE(EXCLUDED.chapter, hs_items.chapter), "
            "  updated_at = NOW()"
        )
        cc.ejecutar_comando_sql(sql, ())

        # Contar
        df1 = cc.ejecutar_consulta_sql("SELECT COUNT(*) AS c FROM hs_items")
        df2 = cc.ejecutar_consulta_sql("SELECT COUNT(DISTINCT hs6) AS c FROM tariff_items")
        return jsonify({
            'code': 200,
            'message': 'Backfill de hs_items completado',
            'details': {
                'hs_items_count': int(df1.iloc[0]['c']) if df1 is not None and not df1.empty else 0,
                'distinct_hs6_in_tariff_items': int(df2.iloc[0]['c']) if df2 is not None and not df2.empty else 0
            }
        }), 200
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en backfill de hs_items',
            'details': str(e)
        }), 500


@bp.route('/admin/sync/dian', methods=['POST'])
@require_auth
@require_role('admin')
def sync_dian():
    """Dispara el proceso de scraping/ingesta DIAN y devuelve el resumen."""
    try:
        ing = DianIngestor(fetched_by='admin_api')
        result = ing.run()
        return jsonify({
            'code': 200,
            'message': 'Sincronización DIAN ejecutada',
            'details': result
        }), 200
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error ejecutando sincronización DIAN',
            'details': str(e)
        }), 500

@bp.route('/params', methods=['POST'])
@require_auth
@require_role('admin')
def update_params():
    """Actualizar parámetros de configuración"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': 'Datos requeridos',
                'details': 'Se requiere un JSON con los parámetros a actualizar'
            }), 400
        
        # Validar parámetros
        allowed_params = ['k', 'umbral', 'max_candidates', 'embedding_model', 'similarity_threshold']
        updated_params = {}
        
        for param, value in data.items():
            if param in allowed_params:
                # Validaciones específicas
                if param == 'k' and (not isinstance(value, int) or value < 1 or value > 20):
                    return jsonify({
                        'code': 400,
                        'message': 'Valor inválido para k',
                        'details': 'k debe ser un entero entre 1 y 20'
                    }), 400
                
                if param == 'umbral' and (not isinstance(value, (int, float)) or value < 0 or value > 1):
                    return jsonify({
                        'code': 400,
                        'message': 'Valor inválido para umbral',
                        'details': 'umbral debe ser un número entre 0 y 1'
                    }), 400
                
                if param == 'max_candidates' and (not isinstance(value, int) or value < 1 or value > 50):
                    return jsonify({
                        'code': 400,
                        'message': 'Valor inválido para max_candidates',
                        'details': 'max_candidates debe ser un entero entre 1 y 50'
                    }), 400
                
                updated_params[param] = value
        
        # Actualizar configuración global
        GLOBAL_CONFIG.update(updated_params)
        
        return jsonify({
            'code': 200,
            'message': 'Parámetros actualizados exitosamente',
            'details': {
                'updated_params': updated_params,
                'current_config': GLOBAL_CONFIG
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error al actualizar parámetros',
            'details': str(e)
        }), 500

@bp.route('/legal-sources', methods=['GET'])
@require_auth
@require_role('admin')
def get_legal_sources():
    """Obtener fuentes legales"""
    try:
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        source_type = request.args.get('type')
        
        # Obtener fuentes legales
        sources = legal_source_repo.find_all(page=page, per_page=per_page)
        
        # Filtrar por tipo si se especifica
        if source_type:
            sources = [s for s in sources if s.get('source_type') == source_type]
        
        # Estadísticas
        stats = {
            'total_sources': len(sources),
            'by_type': {}
        }
        
        for source in sources:
            source_type = source.get('source_type', 'unknown')
            if source_type not in stats['by_type']:
                stats['by_type'][source_type] = 0
            stats['by_type'][source_type] += 1
        
        return jsonify({
            'code': 200,
            'message': 'Fuentes legales obtenidas exitosamente',
            'details': {
                'sources': sources,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': len(sources)
                },
                'statistics': stats
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error al obtener fuentes legales',
            'details': str(e)
        }), 500

@bp.route('/legal-sources', methods=['POST'])
@require_auth
@require_role('admin')
def add_legal_source():
    """Agregar nueva fuente legal"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': 'Datos requeridos',
                'details': 'Se requiere un JSON con los datos de la fuente legal'
            }), 400
        
        # Validar campos requeridos
        required_fields = ['source_type', 'ref_code']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'code': 400,
                    'message': f'Campo requerido: {field}',
                    'details': f'El campo {field} es obligatorio'
                }), 400
        
        # Validar tipo de fuente
        valid_types = ['RGI', 'NOTA', 'RESOLUCION', 'MANUAL', 'OTRO']
        if data['source_type'] not in valid_types:
            return jsonify({
                'code': 400,
                'message': 'Tipo de fuente inválido',
                'details': f'El tipo debe ser uno de: {", ".join(valid_types)}'
            }), 400
        
        # Crear fuente legal
        source_data = {
            'source_type': data['source_type'],
            'ref_code': data['ref_code'],
            'url': data.get('url'),
            'summary': data.get('summary')
        }
        
        source_id = legal_source_repo.create(source_data)
        
        if not source_id:
            return jsonify({
                'code': 500,
                'message': 'Error al crear fuente legal',
                'details': 'No se pudo crear la fuente legal en la base de datos'
            }), 500
        
        # Obtener la fuente creada
        created_source = legal_source_repo.find_by_id(source_id)
        
        return jsonify({
            'code': 201,
            'message': 'Fuente legal creada exitosamente',
            'details': created_source
        }), 201
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error al crear fuente legal',
            'details': str(e)
        }), 500

@bp.route('/embed-hs', methods=['POST'])
@require_auth
@require_role('admin')
def embed_hs_catalog():
    """Recalcular embeddings del catálogo HS"""
    try:
        # Obtener todos los items HS
        hs_items = hs_item_repo.find_all()
        
        if not hs_items:
            return jsonify({
                'code': 404,
                'message': 'No hay items HS',
                'details': 'No se encontraron items del catálogo HS para procesar'
            }), 404
        
        results = {
            'total_items': len(hs_items),
            'processed': 0,
            'errors': 0,
            'errors_details': []
        }
        
        # Procesar cada item
        for item in hs_items:
            try:
                # Crear texto para embedding
                item_text = f"{item.get('title', '')} {item.get('keywords', '')}".strip()
                
                if not item_text:
                    results['errors'] += 1
                    results['errors_details'].append({
                        'hs_code': item.get('hs_code'),
                        'error': 'Texto vacío para embedding'
                    })
                    continue
                
                # Generar embedding
                embedding = embedding_service.generate_embedding(item_text)
                embedding_vector = embedding.tolist()
                
                # Guardar embedding con el mismo provider/model que usa PgVectorIndex
                success = embedding_repo.create_or_update_embedding(
                    owner_type='hs_item',
                    owner_id=item['id'],
                    provider=embedding_service.provider,
                    model=embedding_service.model,
                    vector=json.dumps(embedding_vector),
                    text_norm=item_text[:1000]  # Primeros 1000 caracteres
                )
                
                if success:
                    results['processed'] += 1
                else:
                    results['errors'] += 1
                    results['errors_details'].append({
                        'hs_code': item.get('hs_code'),
                        'error': 'Error al guardar embedding'
                    })
                    
            except Exception as e:
                results['errors'] += 1
                results['errors_details'].append({
                    'hs_code': item.get('hs_code'),
                    'error': str(e)
                })
        
        # Resumen final
        results['success_rate'] = results['processed'] / results['total_items'] if results['total_items'] > 0 else 0
        
        return jsonify({
            'code': 200,
            'message': 'Procesamiento de embeddings completado',
            'details': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en el procesamiento de embeddings',
            'details': str(e)
        }), 500

@bp.route('/embeddings/rebuild', methods=['POST'])
@require_auth
@require_role('admin')
def rebuild_embeddings_tariff_items():
    """Re-embeddea todos los tariff_items con el proveedor/modelo actual sin reingestar PDF.
    Body opcional: {"only_missing": true}
    """
    try:
        data = request.get_json(silent=True) or {}
        only_missing = bool(data.get('only_missing', False))

        ing = DianIngestor(fetched_by='admin_rebuild')

        # Obtener items: id y title desde tariff_items
        items_df = ing.cc.ejecutar_consulta_sql("SELECT id, title FROM tariff_items ORDER BY id")
        if items_df is None or items_df.empty:
            return jsonify({
                'code': 404,
                'message': 'No hay tariff_items',
                'details': 'La tabla tariff_items no tiene registros'
            }), 404

        processed = 0
        skipped = 0
        errors = 0
        errors_details = []

        for _, row in items_df.iterrows():
            tid = int(row['id'])
            title = (row.get('title') or '').strip()
            if not title:
                skipped += 1
                continue
            try:
                if only_missing:
                    q = ("SELECT 1 FROM embeddings WHERE owner_type='tariff_item' AND owner_id = :p0 "
                         "AND provider = :p1 AND model = :p2 LIMIT 1")
                    df = ing.cc.ejecutar_consulta_sql(q, (tid, ing.embed.provider, ing.embed.model))
                    if df is not None and not df.empty:
                        skipped += 1
                        continue
                ing._recalc_embedding_for_tariff_item(tid, title)
                processed += 1
            except Exception as ex:
                errors += 1
                errors_details.append({'item_id': tid, 'error': str(ex)})

        return jsonify({
            'code': 200,
            'message': 'Re-embedding de tariff_items completado',
            'details': {
                'total_items': len(items_df),
                'processed': processed,
                'skipped': skipped,
                'errors': errors,
                'provider': ing.embed.provider,
                'model': ing.embed.model,
                'errors_details': errors_details[:50]
            }
        }), 200
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en re-embedding de tariff_items',
            'details': str(e)
        }), 500

@bp.route('/stats', methods=['GET'])
@require_auth
@require_role('admin')
def get_stats():
    """Obtener estadísticas del sistema"""
    try:
        stats = {
            'database': {},
            'embeddings': {},
            'classification': {}
        }
        
        # Estadísticas de base de datos
        try:
            # Contar registros por tabla
            stats['database']['total_hs_items'] = len(hs_item_repo.find_all())
            stats['database']['total_embeddings'] = len(embedding_repo.find_all())
            stats['database']['total_rgi_rules'] = len(rgi_rule_repo.find_all())
            stats['database']['total_legal_sources'] = len(legal_source_repo.find_all())
        except Exception as e:
            stats['database']['error'] = str(e)
        
        # Estadísticas de embeddings
        try:
            embeddings = embedding_repo.find_all()
            if embeddings:
                stats['embeddings']['total_embeddings'] = len(embeddings)
                stats['embeddings']['by_owner_type'] = {}
                stats['embeddings']['by_provider'] = {}
                
                for emb in embeddings:
                    owner_type = emb.get('owner_type', 'unknown')
                    provider = emb.get('provider', 'unknown')
                    
                    if owner_type not in stats['embeddings']['by_owner_type']:
                        stats['embeddings']['by_owner_type'][owner_type] = 0
                    stats['embeddings']['by_owner_type'][owner_type] += 1
                    
                    if provider not in stats['embeddings']['by_provider']:
                        stats['embeddings']['by_provider'][provider] = 0
                    stats['embeddings']['by_provider'][provider] += 1
        except Exception as e:
            stats['embeddings']['error'] = str(e)
        
        # Configuración actual
        stats['configuration'] = GLOBAL_CONFIG
        
        return jsonify({
            'code': 200,
            'message': 'Estadísticas obtenidas exitosamente',
            'details': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error al obtener estadísticas',
            'details': str(e)
        }), 500

@bp.route('/health', methods=['GET'])
@require_auth
@require_role('admin')
def admin_health():
    """Verificación de salud del sistema (admin)"""
    try:
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': None
        }
        
        from datetime import datetime
        health_status['timestamp'] = datetime.now().isoformat()
        
        # Verificar conexión a base de datos
        try:
            # Intentar obtener un item HS
            test_item = hs_item_repo.find_by_id(1)
            health_status['checks']['database'] = {
                'status': 'ok',
                'message': 'Conexión a base de datos exitosa'
            }
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'error',
                'message': f'Error de conexión: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Verificar servicio de embeddings
        try:
            test_embedding = embedding_service.generate_embedding("test")
            health_status['checks']['embedding_service'] = {
                'status': 'ok',
                'message': 'Servicio de embeddings funcionando'
            }
        except Exception as e:
            health_status['checks']['embedding_service'] = {
                'status': 'error',
                'message': f'Error en servicio de embeddings: {str(e)}'
            }
            health_status['status'] = 'unhealthy'
        
        # Verificar configuración
        health_status['checks']['configuration'] = {
            'status': 'ok',
            'message': 'Configuración válida',
            'details': GLOBAL_CONFIG
        }
        
        return jsonify({
            'code': 200,
            'message': 'Verificación de salud completada',
            'details': health_status
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Error en verificación de salud',
            'details': str(e)
        }), 500
