from typing import Optional

from servicios.control_conexion import ControlConexion


class ValidationRepository:
    """Cerrar caso con final_hs_code (tabla validations y actualización de cases)."""

    def __init__(self):
        self.cc = ControlConexion()

    def close_case(self, case_id: int, validator_id: int, final_hs_code: str, comment: Optional[str] = None) -> bool:
        try:
            # Actualizar caso a 'validated'
            q1 = "UPDATE cases SET status = 'validated', closed_at = NOW(), updated_at = NOW() WHERE id = :p0"
            self.cc.ejecutar_comando_sql(q1, (case_id,))

            # Insertar registro de validación
            q2 = (
                "INSERT INTO validations (case_id, validator_id, final_hs_code, comment, created_at, updated_at) "
                "VALUES (:p0, :p1, :p2, :p3, NOW(), NOW())"
            )
            self.cc.ejecutar_comando_sql(q2, (case_id, validator_id, final_hs_code, comment))
            return True
        except Exception:
            return False
