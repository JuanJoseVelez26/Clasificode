from typing import Optional, Dict, Any, List
from datetime import datetime

from servicios.control_conexion import ControlConexion


class CaseRepository:
    """CRUD de casos (tabla cases)."""

    def __init__(self):
        self.cc = ControlConexion()

    # Lecturas --------------------------------------------------------------
    def get_by_id(self, case_id: int) -> Optional[Dict[str, Any]]:
        q = "SELECT * FROM cases WHERE id = :p0"
        df = self.cc.ejecutar_consulta_sql(q, (case_id,))
        return df.iloc[0].to_dict() if df is not None and not df.empty else None

    def list(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            q = "SELECT * FROM cases WHERE status = :p0 ORDER BY created_at DESC LIMIT :p1 OFFSET :p2"
            df = self.cc.ejecutar_consulta_sql(q, (status, limit, offset))
        else:
            q = "SELECT * FROM cases ORDER BY created_at DESC LIMIT :p0 OFFSET :p1"
            df = self.cc.ejecutar_consulta_sql(q, (limit, offset))
        return df.to_dict('records') if df is not None else []

    # Escrituras ------------------------------------------------------------
    def create(self, data: Dict[str, Any]) -> int:
        q = (
            "INSERT INTO cases (created_by, status, product_title, product_desc, attrs_json, created_at, updated_at) "
            "VALUES (:p0, :p1, :p2, :p3, :p4, NOW(), NOW()) RETURNING id"
        )
        params = (
            int(data['created_by']),
            data.get('status', 'open'),
            data['product_title'],
            data.get('product_desc'),
            data.get('attrs_json'),
        )
        # ejecutar_comando_sql retorna filas afectadas; usamos consulta directa para RETURNING con pandas
        df = self.cc.ejecutar_consulta_sql(q, params)
        return int(df.iloc[0]['id']) if df is not None and not df.empty else 0

    def update(self, case_id: int, data: Dict[str, Any]) -> bool:
        sets = []
        values: List[Any] = []
        for k in ['status', 'product_title', 'product_desc', 'attrs_json']:
            if k in data:
                sets.append(f"{k} = :p{len(values)}")
                values.append(data[k])
        if not sets:
            return False
        values.append(case_id)
        q = f"UPDATE cases SET {', '.join(sets)}, updated_at = NOW() WHERE id = :p{len(values)-1}"
        affected = self.cc.ejecutar_comando_sql(q, tuple(values))
        return affected > 0

    def delete(self, case_id: int) -> bool:
        q = "DELETE FROM cases WHERE id = :p0"
        return self.cc.ejecutar_comando_sql(q, (case_id,)) > 0
