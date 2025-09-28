from typing import List, Dict, Any, Optional

from servicios.control_conexion import ControlConexion


class HSRepository:
    """Consultas de capítulos, partidas, notas y reglas RGI."""

    def __init__(self):
        self.cc = ControlConexion()

    # hs_items --------------------------------------------------------------
    def get_chapter_items(self, chapter: int) -> List[Dict[str, Any]]:
        q = "SELECT * FROM hs_items WHERE chapter = :p0 ORDER BY hs_code"
        df = self.cc.ejecutar_consulta_sql(q, (chapter,))
        return df.to_dict('records') if df is not None else []

    def get_heading_items(self, heading: str) -> List[Dict[str, Any]]:
        """heading de 4 dígitos, ej: '8471'"""
        # hs_code puede estar con puntos, usamos LIKE sobre prefijo 4 dígitos ignorando puntos
        q = (
            "SELECT * FROM hs_items "
            "WHERE replace(hs_code, '.', '') LIKE :p0 || '%' "
            "AND length(replace(hs_code, '.', '')) >= 4 "
            "ORDER BY hs_code"
        )
        df = self.cc.ejecutar_consulta_sql(q, (heading,))
        return df.to_dict('records') if df is not None else []

    def search_by_keywords(self, text: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = (
            "SELECT * FROM hs_items "
            "WHERE title ILIKE :p0 OR keywords ILIKE :p0 "
            "ORDER BY hs_code LIMIT :p1"
        )
        df = self.cc.ejecutar_consulta_sql(q, (f"%{text}%", limit))
        return df.to_dict('records') if df is not None else []

    # hs_notes --------------------------------------------------------------
    def list_notes(self, scope: Optional[str] = None, scope_code: Optional[str] = None) -> List[Dict[str, Any]]:
        base = "SELECT * FROM hs_notes"
        params = []
        where = []
        if scope:
            where.append("scope = :p{}".format(len(params)))
            params.append(scope)
        if scope_code:
            where.append("scope_code = :p{}".format(len(params)))
            params.append(scope_code)
        if where:
            base += " WHERE " + " AND ".join(where)
        base += " ORDER BY scope, scope_code, note_number"
        df = self.cc.ejecutar_consulta_sql(base, tuple(params) if params else None)
        return df.to_dict('records') if df is not None else []

    # rgi_rules -------------------------------------------------------------
    def list_rgi_rules(self) -> List[Dict[str, Any]]:
        q = "SELECT * FROM rgi_rules ORDER BY rgi"
        df = self.cc.ejecutar_consulta_sql(q)
        return df.to_dict('records') if df is not None else []

    # rule_link_hs (opcional) ----------------------------------------------
    def list_rule_links(self) -> List[Dict[str, Any]]:
        try:
            q = "SELECT * FROM rule_link_hs"
            df = self.cc.ejecutar_consulta_sql(q)
            return df.to_dict('records') if df is not None else []
        except Exception:
            return []
