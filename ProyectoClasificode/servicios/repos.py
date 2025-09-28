from typing import List, Optional, Dict, Any, TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from .control_conexion import ControlConexion
import json

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Repositorio base genérico para operaciones CRUD"""
    
    def __init__(self, model_class: type):
        self.model_class = model_class
        self.control_conexion = ControlConexion()
    
    def find_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Buscar por ID"""
        query = f"SELECT * FROM {self.model_class.__tablename__} WHERE id = %s"
        df = self.control_conexion.ejecutar_consulta_sql(query, (id,))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def find_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar todos los registros"""
        query = f"SELECT * FROM {self.model_class.__tablename__}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        df = self.control_conexion.ejecutar_consulta_sql(query)
        return df.to_dict('records')
    
    def create(self, data: Dict[str, Any]) -> int:
        """Crear nuevo registro"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {self.model_class.__tablename__} ({columns}) VALUES ({placeholders}) RETURNING id"
        
        result = self.control_conexion.ejecutar_comando_sql(query, tuple(data.values()))
        return result
    
    def update(self, id: int, data: Dict[str, Any]) -> bool:
        """Actualizar registro"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {self.model_class.__tablename__} SET {set_clause} WHERE id = %s"
        
        values = list(data.values()) + [id]
        result = self.control_conexion.ejecutar_comando_sql(query, tuple(values))
        return result > 0
    
    def delete(self, id: int) -> bool:
        """Eliminar registro"""
        query = f"DELETE FROM {self.model_class.__tablename__} WHERE id = %s"
        result = self.control_conexion.ejecutar_comando_sql(query, (id,))
        return result > 0

class UserRepository(BaseRepository):
    """Repositorio específico para usuarios"""
    
    def __init__(self):
        super().__init__(None)  # No necesitamos model_class para SQL directo
        self.table_name = 'users'
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Buscar usuario por email"""
        query = "SELECT * FROM users WHERE email = %s"
        df = self.control_conexion.ejecutar_consulta_sql(query, (email,))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def find_by_role(self, role: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar usuarios por rol"""
        query = "SELECT * FROM users WHERE role = %s ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        df = self.control_conexion.ejecutar_consulta_sql(query, (role,))
        return df.to_dict('records')
    
    def find_active_users(self) -> List[Dict[str, Any]]:
        """Buscar usuarios activos"""
        query = "SELECT * FROM users WHERE is_active = true ORDER BY created_at DESC"
        df = self.control_conexion.ejecutar_consulta_sql(query)
        return df.to_dict('records')
    
    def update_password(self, user_id: int, password_hash: str) -> bool:
        """Actualizar contraseña de usuario"""
        query = "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s"
        result = self.control_conexion.ejecutar_comando_sql(query, (password_hash, user_id))
        return result > 0
    
    def deactivate_user(self, user_id: int) -> bool:
        """Desactivar usuario"""
        query = "UPDATE users SET is_active = false, updated_at = NOW() WHERE id = %s"
        result = self.control_conexion.ejecutar_comando_sql(query, (user_id,))
        return result > 0

class CaseRepository(BaseRepository):
    """Repositorio específico para casos"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'cases'
    
    def find_by_status(self, status: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar casos por estado"""
        query = "SELECT * FROM cases WHERE status = %s ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        df = self.control_conexion.ejecutar_consulta_sql(query, (status,))
        return df.to_dict('records')
    
    def find_by_creator(self, user_id: int, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar casos creados por un usuario"""
        query = "SELECT * FROM cases WHERE created_by = %s ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        df = self.control_conexion.ejecutar_consulta_sql(query, (user_id,))
        return df.to_dict('records')
    
    def find_open_cases(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar casos abiertos"""
        return self.find_by_status('open', limit)
    
    def close_case(self, case_id: int, final_hs_code: str, validator_id: int) -> bool:
        """Cerrar caso y crear validación"""
        try:
            # Actualizar caso
            case_query = """
            UPDATE cases 
            SET status = 'validated', closed_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """
            self.control_conexion.ejecutar_comando_sql(case_query, (case_id,))
            
            # Crear validación
            validation_query = """
            INSERT INTO validations (case_id, validator_id, final_hs_code, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            """
            self.control_conexion.ejecutar_comando_sql(validation_query, (case_id, validator_id, final_hs_code))
            
            return True
        except Exception:
            return False
    
    def update_attrs(self, case_id: int, attrs: Dict[str, Any]) -> bool:
        """Actualizar atributos JSON del caso"""
        query = "UPDATE cases SET attrs_json = %s, updated_at = NOW() WHERE id = %s"
        result = self.control_conexion.ejecutar_comando_sql(query, (json.dumps(attrs), case_id))
        return result > 0

class CandidateRepository(BaseRepository):
    """Repositorio específico para candidatos"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'candidates'
    
    def find_by_case(self, case_id: int) -> List[Dict[str, Any]]:
        """Buscar candidatos por caso"""
        query = "SELECT * FROM candidates WHERE case_id = %s ORDER BY rank ASC"
        df = self.control_conexion.ejecutar_consulta_sql(query, (case_id,))
        return df.to_dict('records')
    
    def find_by_hs_code(self, hs_code: str) -> List[Dict[str, Any]]:
        """Buscar candidatos por código HS"""
        query = "SELECT * FROM candidates WHERE hs_code = %s ORDER BY confidence DESC"
        df = self.control_conexion.ejecutar_consulta_sql(query, (hs_code,))
        return df.to_dict('records')
    
    def find_top_candidates(self, case_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Buscar los mejores candidatos de un caso"""
        query = "SELECT * FROM candidates WHERE case_id = %s ORDER BY confidence DESC LIMIT %s"
        df = self.control_conexion.ejecutar_consulta_sql(query, (case_id, limit))
        return df.to_dict('records')
    
    def create_candidates_batch(self, candidates: List[Dict[str, Any]]) -> bool:
        """Crear múltiples candidatos en lote"""
        try:
            for candidate in candidates:
                query = """
                INSERT INTO candidates (case_id, hs_code, title, confidence, rationale, legal_refs_json, rank, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                self.control_conexion.ejecutar_comando_sql(query, (
                    candidate['case_id'], candidate['hs_code'], candidate['title'],
                    candidate['confidence'], candidate.get('rationale'), candidate.get('legal_refs_json'),
                    candidate['rank']
                ))
            return True
        except Exception:
            return False

class ValidationRepository(BaseRepository):
    """Repositorio específico para validaciones"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'validations'
    
    def find_by_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        """Buscar validación por caso"""
        query = "SELECT * FROM validations WHERE case_id = %s ORDER BY created_at DESC LIMIT 1"
        df = self.control_conexion.ejecutar_consulta_sql(query, (case_id,))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def find_by_validator(self, validator_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar validaciones por validador"""
        query = "SELECT * FROM validations WHERE validator_id = %s ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        df = self.control_conexion.ejecutar_consulta_sql(query, (validator_id,))
        return df.to_dict('records')

class HSItemRepository(BaseRepository):
    """Repositorio específico para items HS"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'hs_items'
    
    def find_by_hs_code(self, hs_code: str) -> Optional[Dict[str, Any]]:
        """Buscar item por código HS"""
        query = "SELECT * FROM hs_items WHERE hs_code = %s"
        df = self.control_conexion.ejecutar_consulta_sql(query, (hs_code,))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def find_by_chapter(self, chapter: int) -> List[Dict[str, Any]]:
        """Buscar items por capítulo"""
        query = "SELECT * FROM hs_items WHERE chapter = %s ORDER BY hs_code"
        df = self.control_conexion.ejecutar_consulta_sql(query, (chapter,))
        return df.to_dict('records')
    
    def find_by_level(self, level: int) -> List[Dict[str, Any]]:
        """Buscar items por nivel"""
        query = "SELECT * FROM hs_items WHERE level = %s ORDER BY hs_code"
        df = self.control_conexion.ejecutar_consulta_sql(query, (level,))
        return df.to_dict('records')
    
    def search_by_keywords(self, keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar items por palabras clave"""
        query = """
        SELECT * FROM hs_items 
        WHERE keywords ILIKE %s OR title ILIKE %s 
        ORDER BY hs_code 
        LIMIT %s
        """
        search_term = f"%{keywords}%"
        df = self.control_conexion.ejecutar_consulta_sql(query, (search_term, search_term, limit))
        return df.to_dict('records')

class EmbeddingRepository(BaseRepository):
    """Repositorio específico para embeddings"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'embeddings'
    
    def find_by_owner(self, owner_type: str, owner_id: int, provider: str, model: str) -> Optional[Dict[str, Any]]:
        """Buscar embedding por propietario"""
        query = """
        SELECT * FROM embeddings 
        WHERE owner_type = %s AND owner_id = %s AND provider = %s AND model = %s
        """
        df = self.control_conexion.ejecutar_consulta_sql(query, (owner_type, owner_id, provider, model))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def find_similar_vectors(self, query_vector: str, owner_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar vectores similares usando pgvector"""
        query = f"""
        SELECT *, vector <=> '{query_vector}'::vector as distance
        FROM embeddings 
        WHERE owner_type = %s 
        ORDER BY vector <=> '{query_vector}'::vector
        LIMIT %s
        """
        df = self.control_conexion.ejecutar_consulta_sql(query, (owner_type, limit))
        return df.to_dict('records')
    
    def create_or_update_embedding(self, owner_type: str, owner_id: int, provider: str, model: str, 
                                 dim: int, vector: str, text_norm: str) -> bool:
        """Crear o actualizar embedding"""
        query = """
        INSERT INTO embeddings (owner_type, owner_id, provider, model, dim, vector, text_norm, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s::vector, %s, NOW(), NOW())
        ON CONFLICT (owner_type, owner_id, provider, model) 
        DO UPDATE SET 
            dim = EXCLUDED.dim,
            vector = EXCLUDED.vector,
            text_norm = EXCLUDED.text_norm,
            updated_at = NOW()
        """
        try:
            self.control_conexion.ejecutar_comando_sql(query, (owner_type, owner_id, provider, model, dim, vector, text_norm))
            return True
        except Exception:
            return False

class RGIRuleRepository(BaseRepository):
    """Repositorio específico para reglas RGI"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'rgi_rules'
    
    def find_by_rgi(self, rgi: str) -> Optional[Dict[str, Any]]:
        """Buscar regla por RGI"""
        query = "SELECT * FROM rgi_rules WHERE rgi = %s"
        df = self.control_conexion.ejecutar_consulta_sql(query, (rgi,))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def find_all_rgi_types(self) -> List[str]:
        """Obtener todos los tipos de RGI"""
        query = "SELECT DISTINCT rgi FROM rgi_rules ORDER BY rgi"
        df = self.control_conexion.ejecutar_consulta_sql(query)
        return df['rgi'].tolist()

class LegalSourceRepository(BaseRepository):
    """Repositorio específico para fuentes legales"""
    
    def __init__(self):
        super().__init__(None)
        self.table_name = 'legal_sources'
    
    def find_by_type(self, source_type: str) -> List[Dict[str, Any]]:
        """Buscar fuentes por tipo"""
        query = "SELECT * FROM legal_sources WHERE source_type = %s ORDER BY created_at DESC"
        df = self.control_conexion.ejecutar_consulta_sql(query, (source_type,))
        return df.to_dict('records')
    
    def find_by_ref_code(self, ref_code: str) -> Optional[Dict[str, Any]]:
        """Buscar fuente por código de referencia"""
        query = "SELECT * FROM legal_sources WHERE ref_code = %s"
        df = self.control_conexion.ejecutar_consulta_sql(query, (ref_code,))
        return df.iloc[0].to_dict() if not df.empty else None
    
    def update_content_hash(self, source_id: int, content_hash: str) -> bool:
        """Actualizar hash del contenido"""
        query = "UPDATE legal_sources SET content_hash = %s, updated_at = NOW() WHERE id = %s"
        result = self.control_conexion.ejecutar_comando_sql(query, (content_hash, source_id))
        return result > 0
