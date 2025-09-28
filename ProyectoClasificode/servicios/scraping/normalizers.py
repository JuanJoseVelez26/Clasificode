import re
from datetime import datetime
from typing import Optional


def clean_code(code: str) -> str:
    """Normaliza un código arancelario a solo dígitos, sin puntos, y devuelve.
    No trunca longitud: útil para detectar 8-10 dígitos.
    """
    if not code:
        return ''
    digits = re.sub(r"\D", "", str(code))
    return digits


def to_hs6(code: str) -> str:
    d = clean_code(code)
    return d[:6] if len(d) >= 6 else d


def to_national10(code: str) -> str:
    d = clean_code(code)
    return d[:10] if len(d) >= 10 else d


def parse_date(value: str) -> Optional[datetime]:
    """Convierte textos de fechas comunes a datetime. Devuelve None si no se puede."""
    if not value:
        return None
    value = value.strip()
    fmts = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def normalize_title(text: str) -> str:
    return (text or '').strip()
