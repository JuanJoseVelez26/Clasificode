from typing import List, Dict, Any, Optional

from servicios.control_conexion import ControlConexion


class TariffRepository:
    """Consultas sobre aperturas nacionales (vista v_current_tariff_items)."""

    def __init__(self):
        self.cc = ControlConexion()

    def list_current_by_hs6(self, hs6: str) -> List[Dict[str, Any]]:
        q = (
            "SELECT * FROM v_current_tariff_items "
            "WHERE substring(national_code, 1, 6) = :p0 "
            "ORDER BY national_code"
        )
        df = self.cc.ejecutar_consulta_sql(q, (hs6,))
        return df.to_dict('records') if df is not None else []

    def get_by_national_code(self, national_code: str) -> Optional[Dict[str, Any]]:
        q = "SELECT * FROM v_current_tariff_items WHERE national_code = :p0 LIMIT 1"
        df = self.cc.ejecutar_consulta_sql(q, (national_code,))
        return df.iloc[0].to_dict() if df is not None and not df.empty else None
