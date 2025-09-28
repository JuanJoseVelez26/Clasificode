from typing import Optional, Dict, Any, List

from servicios.control_conexion import ControlConexion


class EmbeddingRepository:
    """Upsert y query de embeddings (tabla embeddings)."""

    def __init__(self):
        self.cc = ControlConexion()

    def upsert(self, owner_type: str, owner_id: int, provider: str, model: str,
               dim: int, vector_json: str, text_norm: str) -> bool:
        q = (
            "INSERT INTO embeddings (owner_type, owner_id, provider, model, dim, vector, text_norm, created_at, updated_at) "
            "VALUES (:p0, :p1, :p2, :p3, :p4, (:p5)::vector, :p6, NOW(), NOW()) "
            "ON CONFLICT (owner_type, owner_id, provider, model) DO UPDATE SET "
            "dim = EXCLUDED.dim, vector = EXCLUDED.vector, text_norm = EXCLUDED.text_norm, updated_at = NOW()"
        )
        try:
            return self.cc.ejecutar_comando_sql(q, (owner_type, owner_id, provider, model, dim, vector_json, text_norm)) > 0
        except Exception:
            return False

    def get_by_owner(self, owner_type: str, owner_id: int, provider: str, model: str) -> Optional[Dict[str, Any]]:
        q = (
            "SELECT * FROM embeddings WHERE owner_type = :p0 AND owner_id = :p1 AND provider = :p2 AND model = :p3"
        )
        df = self.cc.ejecutar_consulta_sql(q, (owner_type, owner_id, provider, model))
        return df.iloc[0].to_dict() if df is not None and not df.empty else None

    def find_similar(self, query_vector_json: str, owner_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = (
            "SELECT *, vector <=> (:p0)::vector AS distance FROM embeddings "
            "WHERE owner_type = :p1 ORDER BY vector <=> (:p0)::vector LIMIT :p2"
        )
        df = self.cc.ejecutar_consulta_sql(q, (query_vector_json, owner_type, limit))
        return df.to_dict('records') if df is not None else []
