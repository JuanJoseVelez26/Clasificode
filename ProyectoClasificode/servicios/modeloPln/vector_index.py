import json
import numpy as np
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from servicios.control_conexion import ControlConexion

class PgVectorIndex:
    """Índice vectorial usando PostgreSQL con pgvector"""
    
    def __init__(self):
        self.control_conexion = ControlConexion()
        self._ensure_vector_extension()
    
    def _ensure_vector_extension(self):
        """Asegurar que la extensión pgvector esté instalada"""
        try:
            query = "CREATE EXTENSION IF NOT EXISTS vector;"
            self.control_conexion.ejecutar_comando_sql(query)
        except Exception as e:
            print(f"Advertencia: No se pudo crear la extensión vector: {e}")
    
    def upsert(self, owner_type: str, owner_id: int, vector: Union[np.ndarray, List[float]], 
               meta: Dict[str, Any] = None) -> bool:
        """Insertar o actualizar vector en el índice"""
        try:
            # Convertir vector a lista si es numpy array
            if isinstance(vector, np.ndarray):
                vector_list = vector.tolist()
            else:
                vector_list = vector
            
            # Convertir vector a formato pgvector
            vector_str = f"[{','.join(map(str, vector_list))}]"
            
            # Preparar metadatos
            meta_json = json.dumps(meta) if meta else None
            
            # Verificar si ya existe
            check_query = """
            SELECT id FROM embeddings 
            WHERE owner_type = %s AND owner_id = %s
            """
            df = self.control_conexion.ejecutar_consulta_sql(check_query, (owner_type, owner_id))
            
            if not df.empty:
                # Actualizar existente
                update_query = """
                UPDATE embeddings 
                SET vector = %s::vector, meta = %s, updated_at = NOW()
                WHERE owner_type = %s AND owner_id = %s
                """
                self.control_conexion.ejecutar_comando_sql(
                    update_query, (vector_str, meta_json, owner_type, owner_id)
                )
            else:
                # Insertar nuevo
                insert_query = """
                INSERT INTO embeddings (owner_type, owner_id, vector, meta, created_at, updated_at)
                VALUES (%s, %s, %s::vector, %s, NOW(), NOW())
                """
                self.control_conexion.ejecutar_comando_sql(
                    insert_query, (owner_type, owner_id, vector_str, meta_json)
                )
            
            return True
            
        except Exception as e:
            print(f"Error en upsert vector: {e}")
            return False
    
    def knn_for_hs(self, qvec: Union[np.ndarray, List[float]], provider: str, model: str, 
                   k: int = 5, distance_metric: str = 'cosine') -> List[Dict[str, Any]]:
        """Búsqueda KNN para códigos HS usando pgvector"""
        try:
            # Convertir vector de consulta
            if isinstance(qvec, np.ndarray):
                qvec_list = qvec.tolist()
            else:
                qvec_list = qvec
            
            qvec_str = f"[{','.join(map(str, qvec_list))}]"
            
            # Construir query según métrica de distancia
            if distance_metric == 'cosine':
                distance_expr = "vector <=> %s::vector"
            elif distance_metric == 'l2':
                distance_expr = "vector <-> %s::vector"
            elif distance_metric == 'dot':
                distance_expr = "vector <#> %s::vector"
            else:
                distance_expr = "vector <=> %s::vector"  # Default a cosine
            
            query = f"""
            SELECT 
                hi.hs_code,
                hi.title,
                hi.keywords,
                ev.owner_id,
                ev.vector {distance_expr} AS distance,
                ev.meta
            FROM embeddings ev 
            JOIN hs_items hi ON hi.id = ev.owner_id 
            WHERE ev.owner_type = 'hs_item' 
            AND ev.provider = %s 
            AND ev.model = %s 
            ORDER BY ev.vector {distance_expr}
            LIMIT %s
            """
            
            # Ejecutar query
            df = self.control_conexion.ejecutar_consulta_sql(
                query, (qvec_str, provider, model, qvec_str, k)
            )
            
            # Convertir resultados
            results = []
            for _, row in df.iterrows():
                result = {
                    'hs_code': row['hs_code'],
                    'title': row['title'],
                    'keywords': row['keywords'],
                    'owner_id': row['owner_id'],
                    'distance': float(row['distance']),
                    'meta': json.loads(row['meta']) if row['meta'] else {}
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error en KNN search: {e}")
            return []
    
    def search_similar_vectors(self, query_vector: Union[np.ndarray, List[float]], 
                              owner_type: str = None, provider: str = None, model: str = None,
                              k: int = 10, distance_metric: str = 'cosine') -> List[Dict[str, Any]]:
        """Búsqueda general de vectores similares"""
        try:
            # Convertir vector de consulta
            if isinstance(query_vector, np.ndarray):
                qvec_list = query_vector.tolist()
            else:
                qvec_list = query_vector
            
            qvec_str = f"[{','.join(map(str, qvec_list))}]"
            
            # Construir query dinámica
            where_conditions = []
            params = [qvec_str]
            
            if owner_type:
                where_conditions.append("ev.owner_type = %s")
                params.append(owner_type)
            
            if provider:
                where_conditions.append("ev.provider = %s")
                params.append(provider)
            
            if model:
                where_conditions.append("ev.model = %s")
                params.append(model)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Construir expresión de distancia
            if distance_metric == 'cosine':
                distance_expr = "vector <=> %s::vector"
            elif distance_metric == 'l2':
                distance_expr = "vector <-> %s::vector"
            elif distance_metric == 'dot':
                distance_expr = "vector <#> %s::vector"
            else:
                distance_expr = "vector <=> %s::vector"
            
            query = f"""
            SELECT 
                ev.owner_type,
                ev.owner_id,
                ev.provider,
                ev.model,
                ev.vector {distance_expr} AS distance,
                ev.meta,
                ev.created_at
            FROM embeddings ev 
            WHERE {where_clause}
            ORDER BY ev.vector {distance_expr}
            LIMIT %s
            """
            
            params.append(k)
            
            # Ejecutar query
            df = self.control_conexion.ejecutar_consulta_sql(query, tuple(params))
            
            # Convertir resultados
            results = []
            for _, row in df.iterrows():
                result = {
                    'owner_type': row['owner_type'],
                    'owner_id': row['owner_id'],
                    'provider': row['provider'],
                    'model': row['model'],
                    'distance': float(row['distance']),
                    'meta': json.loads(row['meta']) if row['meta'] else {},
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error en search_similar_vectors: {e}")
            return []
    
    def batch_upsert(self, vectors_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Insertar o actualizar múltiples vectores en lote"""
        success_count = 0
        error_count = 0
        
        for vector_data in vectors_data:
            try:
                success = self.upsert(
                    owner_type=vector_data['owner_type'],
                    owner_id=vector_data['owner_id'],
                    vector=vector_data['vector'],
                    meta=vector_data.get('meta')
                )
                if success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"Error en batch upsert: {e}")
                error_count += 1
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'total_count': len(vectors_data)
        }
    
    def delete_vector(self, owner_type: str, owner_id: int) -> bool:
        """Eliminar vector del índice"""
        try:
            query = "DELETE FROM embeddings WHERE owner_type = %s AND owner_id = %s"
            self.control_conexion.ejecutar_comando_sql(query, (owner_type, owner_id))
            return True
        except Exception as e:
            print(f"Error eliminando vector: {e}")
            return False
    
    def get_vector_info(self, owner_type: str, owner_id: int) -> Optional[Dict[str, Any]]:
        """Obtener información de un vector específico"""
        try:
            query = """
            SELECT owner_type, owner_id, provider, model, meta, created_at, updated_at
            FROM embeddings 
            WHERE owner_type = %s AND owner_id = %s
            """
            df = self.control_conexion.ejecutar_consulta_sql(query, (owner_type, owner_id))
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    'owner_type': row['owner_type'],
                    'owner_id': row['owner_id'],
                    'provider': row['provider'],
                    'model': row['model'],
                    'meta': json.loads(row['meta']) if row['meta'] else {},
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo vector info: {e}")
            return None
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del índice vectorial"""
        try:
            # Contar total de vectores
            count_query = "SELECT COUNT(*) as total FROM embeddings"
            count_df = self.control_conexion.ejecutar_consulta_sql(count_query)
            total_vectors = count_df.iloc[0]['total'] if not count_df.empty else 0
            
            # Contar por owner_type
            type_query = """
            SELECT owner_type, COUNT(*) as count 
            FROM embeddings 
            GROUP BY owner_type
            """
            type_df = self.control_conexion.ejecutar_consulta_sql(type_query)
            by_type = {row['owner_type']: row['count'] for _, row in type_df.iterrows()}
            
            # Contar por provider
            provider_query = """
            SELECT provider, COUNT(*) as count 
            FROM embeddings 
            GROUP BY provider
            """
            provider_df = self.control_conexion.ejecutar_consulta_sql(provider_query)
            by_provider = {row['provider']: row['count'] for _, row in provider_df.iterrows()}
            
            # Contar por model
            model_query = """
            SELECT model, COUNT(*) as count 
            FROM embeddings 
            GROUP BY model
            """
            model_df = self.control_conexion.ejecutar_consulta_sql(model_query)
            by_model = {row['model']: row['count'] for _, row in model_df.iterrows()}
            
            return {
                'total_vectors': total_vectors,
                'by_owner_type': by_type,
                'by_provider': by_provider,
                'by_model': by_model,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {
                'total_vectors': 0,
                'by_owner_type': {},
                'by_provider': {},
                'by_model': {},
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def create_indexes(self) -> bool:
        """Crear índices vectoriales para optimizar búsquedas"""
        try:
            # Índice para búsqueda por owner_type y provider
            index1_query = """
            CREATE INDEX IF NOT EXISTS idx_embeddings_owner_provider 
            ON embeddings (owner_type, provider, model)
            """
            self.control_conexion.ejecutar_comando_sql(index1_query)
            
            # Índice vectorial para búsquedas KNN
            index2_query = """
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine 
            ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)
            """
            self.control_conexion.ejecutar_comando_sql(index2_query)
            
            # Índice vectorial para distancia L2
            index3_query = """
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector_l2 
            ON embeddings USING ivfflat (vector vector_l2_ops) WITH (lists = 100)
            """
            self.control_conexion.ejecutar_comando_sql(index3_query)
            
            return True
            
        except Exception as e:
            print(f"Error creando índices: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Probar conexión y funcionalidad del índice vectorial"""
        try:
            # Verificar extensión vector
            ext_query = "SELECT * FROM pg_extension WHERE extname = 'vector'"
            ext_df = self.control_conexion.ejecutar_consulta_sql(ext_query)
            vector_available = not ext_df.empty
            
            # Verificar tabla embeddings
            table_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'embeddings'
            )
            """
            table_df = self.control_conexion.ejecutar_consulta_sql(table_query)
            table_exists = table_df.iloc[0][0] if not table_df.empty else False
            
            # Probar inserción de vector de prueba
            test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
            test_success = self.upsert('test', 999, test_vector, {'test': True})
            
            # Limpiar vector de prueba
            if test_success:
                self.delete_vector('test', 999)
            
            return {
                'status': 'success' if vector_available and table_exists else 'partial',
                'vector_extension': vector_available,
                'embeddings_table': table_exists,
                'test_upsert': test_success,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
