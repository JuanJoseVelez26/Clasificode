import io
import re
import json
from typing import Dict, Any, List, Optional, Tuple

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    from pdfminer.high_level import extract_text
except Exception:  # pragma: no cover
    extract_text = None

from .normalizers import clean_code, to_hs6, to_national10, parse_date, normalize_title


def _download_bytes(url: str) -> bytes:
    if not requests:
        return b""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def _pdf_to_text(pdf_bytes: bytes) -> str:
    if not extract_text:
        return ""
    return extract_text(io.BytesIO(pdf_bytes))


def extract_items_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extrae items desde texto usando regex tolerantes:
    - HS6: primeras 6 cifras relevantes (con o sin puntos/espacios)
    - Código nacional: 10 dígitos (con o sin puntos/espacios)
    - Título: misma línea o la siguiente no vacía
    - Vigencias: buscar en una ventana de ±2 líneas
    """
    items: List[Dict[str, Any]] = []
    if not text:
        return items

    # Patrones
    # HS6 tolerante: 6 dígitos potencialmente con puntos/espacios, bordeando palabra
    hs6_re = re.compile(r"(?P<hs6>(?:\d[\.\s-]?){6})(?!\d)")
    # Nacional 10 dígitos tolerante
    nat10_re = re.compile(r"(?P<nat>(?:\d[\.\s-]?){10,12})(?!\d)")

    lines = text.splitlines()
    n = len(lines)

    def pick_title(idx: int) -> str:
        # Toma la línea actual o la siguiente no vacía como título
        cur = lines[idx].strip()
        if len(cur) >= 6:
            return normalize_title(cur)
        j = idx + 1
        while j < n and len(lines[j].strip()) < 6:
            j += 1
        return normalize_title(lines[j]) if j < n else normalize_title(cur)

    # 1) Buscar primero nacionales de 10 dígitos y derivar HS6
    for i, line in enumerate(lines):
        for m in nat10_re.finditer(line):
            raw_nat = m.group('nat')
            nat_digits = clean_code(raw_nat)
            if len(nat_digits) < 10:
                continue
            national = to_national10(nat_digits)
            hs6 = to_hs6(nat_digits[:6])
            title = pick_title(i)

            # Vigencias en ventana
            window = '\n'.join(lines[max(0, i - 2): min(n, i + 3)])
            vf = None
            vt = None
            m_from = re.search(r"vigenc\w*\s*(desde|a partir de)\s*([\d/.-]{8,10})", window, flags=re.I)
            if m_from:
                vf = parse_date(m_from.group(2))
            m_to = re.search(r"vigenc\w*\s*(hasta)\s*([\d/.-]{8,10})", window, flags=re.I)
            if m_to:
                vt = parse_date(m_to.group(2))

            items.append({
                'hs6': hs6,
                'national_code': national,
                'title': title,
                'notes': '',
                'valid_from': vf.isoformat() if vf else None,
                'valid_to': vt.isoformat() if vt else None,
            })

    # 2) Si no hubo nacionales explícitos, buscar HS6 y luego un nacional cercano en siguientes líneas
    if not items:
        for i, line in enumerate(lines):
            m6 = hs6_re.search(line)
            if not m6:
                continue
            raw_hs6 = m6.group('hs6')
            hs6_digits = clean_code(raw_hs6)
            if len(hs6_digits) < 6:
                continue
            hs6 = to_hs6(hs6_digits)

            # Buscar nacional en las siguientes 5 líneas
            nat_found: Optional[str] = None
            for j in range(i, min(n, i + 6)):
                for mn in nat10_re.finditer(lines[j]):
                    nat_digits = clean_code(mn.group('nat'))
                    if len(nat_digits) >= 10 and nat_digits.startswith(hs6_digits[:6]):
                        nat_found = to_national10(nat_digits)
                        title = pick_title(j)
                        window = '\n'.join(lines[max(0, j - 2): min(n, j + 3)])
                        vf = None
                        vt = None
                        m_from = re.search(r"vigenc\w*\s*(desde|a partir de)\s*([\d/.-]{8,10})", window, flags=re.I)
                        if m_from:
                            vf = parse_date(m_from.group(2))
                        m_to = re.search(r"vigenc\w*\s*(hasta)\s*([\d/.-]{8,10})", window, flags=re.I)
                        if m_to:
                            vt = parse_date(m_to.group(2))

                        items.append({
                            'hs6': hs6,
                            'national_code': nat_found,
                            'title': title,
                            'notes': '',
                            'valid_from': vf.isoformat() if vf else None,
                            'valid_to': vt.isoformat() if vt else None,
                        })
                        break
                if nat_found:
                    break

    # Depuración liviana: evitar ruidos excesivos
    try:
        print(json.dumps({
            'parser_stats': {
                'total_items': len(items)
            }
        }, ensure_ascii=False))
    except Exception:
        pass

    return items


def parse_pdf_or_html(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recibe {'content_type': 'pdf'|'html', 'content': bytes|str|url}
    Devuelve {'items': [...], 'raw_text': str}
    """
    ctype = source.get('content_type')
    content = source.get('content')

    if ctype == 'pdf':
        # content puede ser bytes o URL
        if isinstance(content, str) and content.lower().startswith('http'):
            try:
                pdf_bytes = _download_bytes(content)
            except Exception:
                pdf_bytes = b''
        elif isinstance(content, (bytes, bytearray)):
            pdf_bytes = bytes(content)
        else:
            pdf_bytes = b''
        text = _pdf_to_text(pdf_bytes)
        items = extract_items_from_text(text)
        return { 'items': items, 'raw_text': text or '', 'raw_bytes': pdf_bytes }

    # HTML
    html = content or ''
    # Extraer texto plano simple para regex
    # Quitar tags básicos
    text = re.sub(r"<[^>]+>", "\n", str(html))
    items = extract_items_from_text(text)
    return { 'items': items, 'raw_text': text or '' }
