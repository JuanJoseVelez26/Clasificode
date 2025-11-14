from typing import Dict, Any
import logging

from servicios.control_conexion import ControlConexion


class CandidateRepository:
    """Upsert top1 para candidatos (tabla candidates)."""

    def __init__(self):
        self.cc = ControlConexion()

    def _case_exists(self, case_id: int) -> bool:
        try:
            result = self.cc.ejecutar_escalares(
                "SELECT 1 FROM cases WHERE id = :p0 LIMIT 1",
                {"p0": case_id}
            )
            return result is not None
        except Exception as exc:
            logging.warning(f"[CandidateRepository] Error verificando existencia de caso {case_id}: {exc}")
            return False

    def upsert_top1(self, case_id: int, hs_code: str, title: str, confidence: float,
                    rationale: str, legal_refs_json: str) -> bool:
        # El esquema original define unique(case_id, rank). Usamos rank=1.
        if not self._case_exists(case_id):
            logging.warning(f"[CandidateRepository] Omitiendo registro de candidate por case_id inexistente ({case_id})")
            return False

        q = (
            "INSERT INTO candidates (case_id, hs_code, title, confidence, rationale, legal_refs_json, rank, created_at, updated_at) "
            "VALUES (:p0, :p1, :p2, :p3, :p4, :p5, 1, NOW(), NOW()) "
            "ON CONFLICT (case_id, rank) DO UPDATE SET "
            "hs_code = EXCLUDED.hs_code, title = EXCLUDED.title, confidence = EXCLUDED.confidence, "
            "rationale = EXCLUDED.rationale, legal_refs_json = EXCLUDED.legal_refs_json, updated_at = NOW()"
        )
        try:
            return self.cc.ejecutar_comando_sql(q, (case_id, hs_code, title, confidence, rationale, legal_refs_json)) > 0
        except Exception:
            return False
