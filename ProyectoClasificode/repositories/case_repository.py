from typing import Optional, Dict, Any, List
from datetime import datetime

from servicios.control_conexion import ControlConexion


class CaseRepository:
    """CRUD de casos (tabla cases)."""

    def __init__(self):
        self.cc = ControlConexion()

    # Lecturas --------------------------------------------------------------
    def get_by_id(self, case_id: int) -> Optional[Dict[str, Any]]:
        q = "SELECT * FROM cases WHERE id = :id"
        df = self.cc.ejecutar_consulta_sql(q, {"id": int(case_id)})
        return df.iloc[0].to_dict() if df is not None and not df.empty else None

    def list(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            q = "SELECT * FROM cases WHERE status = :status ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            df = self.cc.ejecutar_consulta_sql(q, {"status": status, "lim": int(limit), "off": int(offset)})
        else:
            q = "SELECT * FROM cases ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            df = self.cc.ejecutar_consulta_sql(q, {"lim": int(limit), "off": int(offset)})
        return df.to_dict('records') if df is not None else []

    # Escrituras ------------------------------------------------------------
    def create(self, data: Dict[str, Any]) -> int:
        q = (
            "INSERT INTO cases (created_by, status, product_title, product_desc, attrs_json, created_at, updated_at) "
            "VALUES (:created_by, :status, :product_title, :product_desc, :attrs_json, NOW(), NOW()) RETURNING id"
        )
        params = {
            "created_by": int(data['created_by']),
            "status": data.get('status', 'open'),
            "product_title": data['product_title'],
            "product_desc": data.get('product_desc'),
            "attrs_json": data.get('attrs_json'),
        }
        # ejecutar_comando_sql retorna filas afectadas; usamos consulta directa para RETURNING con pandas
        df = self.cc.ejecutar_consulta_sql(q, params)
        return int(df.iloc[0]['id']) if df is not None and not df.empty else 0

    def update(self, case_id: int, data: Dict[str, Any]) -> bool:
        sets = []
        values: List[Any] = []
        for k in ['status', 'product_title', 'product_desc', 'attrs_json']:
            if k in data:
                sets.append(f"{k} = :{k}")
                values.append((k, data[k]))
        if not sets:
            return False
        params = {k: v for k, v in values}
        params['id'] = int(case_id)
        q = f"UPDATE cases SET {', '.join(sets)}, updated_at = NOW() WHERE id = :id"
        affected = self.cc.ejecutar_comando_sql(q, params)
        return affected > 0

    def delete(self, case_id: int) -> bool:
        q = "DELETE FROM cases WHERE id = :id"
        return self.cc.ejecutar_comando_sql(q, {"id": int(case_id)}) > 0
