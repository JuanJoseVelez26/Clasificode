from dataclasses import dataclass
from typing import Optional, Dict, Any

from .case import validate_attrs


@dataclass
class ValidationCreate:
    case_id: int
    validator_id: int
    final_hs_code: str  # puede ser nacional de 10 dígitos
    comment: Optional[str] = None
    attrs_json: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if not isinstance(self.case_id, int):
            raise ValueError("case_id debe ser entero")
        if not isinstance(self.validator_id, int):
            raise ValueError("validator_id debe ser entero")
        if not isinstance(self.final_hs_code, str) or not self.final_hs_code:
            raise ValueError("final_hs_code es requerido y debe ser string")
        if self.attrs_json is not None:
            self.attrs_json = validate_attrs(self.attrs_json)
