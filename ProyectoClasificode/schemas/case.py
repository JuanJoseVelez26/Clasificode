from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def validate_attrs(attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Valida y normaliza attrs_json con campos esperados.
    Campos esperados: uso, presentacion, material_predominante, estado, pais_origen
    """
    attrs = attrs or {}
    allowed = {
        'uso': str,
        'presentacion': str,
        'material_predominante': str,
        'estado': str,
        'pais_origen': str,
    }
    normalized: Dict[str, Any] = {}
    for key, typ in allowed.items():
        val = attrs.get(key)
        if val is None:
            continue
        # Coerce a string básica
        normalized[key] = str(val).strip()
    return normalized


@dataclass
class CaseCreate:
    created_by: int
    product_title: str
    product_desc: Optional[str] = None
    attrs_json: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        self.attrs_json = validate_attrs(self.attrs_json)
        if not self.product_title or not isinstance(self.product_title, str):
            raise ValueError("product_title es requerido y debe ser string")
        if not isinstance(self.created_by, int):
            raise ValueError("created_by debe ser entero")


@dataclass
class CaseOut:
    id: int
    status: str
    product_title: str
    product_desc: Optional[str]
    attrs_json: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'status': self.status,
            'product_title': self.product_title,
            'product_desc': self.product_desc,
            'attrs_json': validate_attrs(self.attrs_json),
        }
