"""
Motor de Reglas Generales de Interpretación (RGI) del Arancel

Implementación funcional (funciones puras) que aplican RGI 1, 2, 3 y 6
para filtrar y decidir un código HS6. Mantiene trazabilidad con referencias
legales: rgi_id, note_id, legal_source_id.

Citas (Decreto 1881 de 2021, Arancel de Aduanas 2022-2026):
- RGI 1: "Los títulos de las Secciones, Capítulos y Subcapítulos no tienen
  valor legal; la clasificación de las mercancías se determinará legalmente
  por los textos de las partidas y de las Notas de Sección o de Capítulo y,
  si no son contrarias a los textos de dichas partidas y Notas, de acuerdo
  con las reglas siguientes."
- RGI 2(a): Incompletos/desarmados.
- RGI 2(b): Mezclas y mercancías compuestas.
- RGI 3(a): La partida más específica tendrá prioridad sobre las partidas de
  alcance más genérico.
- RGI 3(b): Carácter esencial de los conjuntos o mezclas.
- RGI 3(c): Si no es posible la clasificación por 3(a) o 3(b), se clasificará
  por la última partida por orden de numeración.
- RGI 6: La clasificación en subpartidas está determinada legalmente por los
  textos de estas subpartidas y de las Notas de subpartida y, mutatis mutandis,
  por las reglas anteriores, considerándose únicamente subpartidas del mismo
  nivel.
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple

from ..control_conexion import ControlConexion

# Tipos simples
Candidate = Dict[str, Any]  # {'hs_code': 'XXXX.XX.XX', 'title': str, 'score': float, 'meta': {...}}
TraceStep = Dict[str, Any]  # {'rgi': 'RGI1', 'decision': str, 'affected': [...], 'legal_refs': {...}}


# Utilidades ---------------------------------------------------------------
def _clean_hs(code: str) -> str:
    if not code:
        return ''
    # Normaliza a formato HS con puntos y garantiza sólo dígitos
    keep = [c for c in code if c.isdigit()]
    s = ''.join(keep)
    # Inserta puntos 2-2-2 (HS6) o mantiene puntos existentes si ya viene con 8/10
    if len(s) >= 6:
        return f"{s[0:2]}.{s[2:4]}.{s[4:6]}"
    if len(s) == 4:
        return f"{s[0:2]}.{s[2:4]}"
    return s


def _hs_chapter(code: str) -> str:
    c = _clean_hs(code)
    return c[0:2] if len(c) >= 2 else ''


def _hs_heading(code: str) -> str:
    c = _clean_hs(code)
    return c[0:2] + c[3:5] if len(c) >= 5 else ''  # e.g., '84' + '71' -> '8471'


def _hs6(code: str) -> str:
    c = _clean_hs(code)
    return c[0:2] + c[3:5] + c[6:8] if len(c) >= 8 else ''  # '847130' -> '847130'


def _fetch_df(cc: ControlConexion, query: str, params: Tuple = ()):
    try:
        return cc.ejecutar_consulta_sql(query, params)
    except Exception:
        # Tolerante a ausencia de tablas durante desarrollo
        import pandas as pd
        return pd.DataFrame()


def _fetch_rgi_map(cc: ControlConexion) -> Dict[str, int]:
    """Devuelve un mapa {'RGI1': id, 'RGI2A': id, ...} si existen."""
    df = _fetch_df(cc, "SELECT id, rgi FROM rgi_rules")
    mapping: Dict[str, int] = {}
    if not df.empty:
        for _, r in df.iterrows():
            mapping[str(r['rgi']).upper()] = int(r['id'])
    return mapping


def _keyword_candidates(cc: ControlConexion, text: str, limit: int = 50) -> List[Candidate]:
    """Búsqueda simple por keywords sobre hs_items.title y hs_items.keywords."""
    text = (text or '').strip()
    if not text:
        return []
    q = (
        "SELECT id, hs_code, title, keywords, level, chapter FROM hs_items "
        "WHERE title ILIKE %s OR keywords ILIKE %s ORDER BY hs_code LIMIT %s"
    )
    df = _fetch_df(cc, q, (f"%{text}%", f"%{text}%", limit))
    out: List[Candidate] = []
    if not df.empty:
        for _, r in df.iterrows():
            hs_code = str(r['hs_code'])
            out.append({
                'hs_code': _clean_hs(hs_code),
                'title': r.get('title'),
                'score': 1.0,
                'meta': {
                    'id': int(r['id']),
                    'level': int(r.get('level') or 0),
                    'chapter': int(r.get('chapter') or 0),
                    'keywords': r.get('keywords')
                }
            })
    return out


def _load_notes_links(cc: ControlConexion) -> Tuple[Any, Any]:
    notes = _fetch_df(cc, "SELECT id, scope, scope_code, note_number, text FROM hs_notes")
    # Tabla relacional opcional rule_link_hs (si existe): rule_id, note_id, hs_code
    links = _fetch_df(cc, "SELECT * FROM rule_link_hs")
    return notes, links


def _trace(steps: List[TraceStep], rgi: str, decision: str, affected: List[str], legal_refs: Dict[str, List[int]]):
    steps.append({
        'rgi': rgi,
        'decision': decision,
        'affected': affected,
        'legal_refs': legal_refs,
    })


# RGI 1 -------------------------------------------------------------------
def apply_rgi1(description: str, extra_texts: List[str] | None = None) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 1 con apoyo en textos legales y Notas (de Sección/Capítulo/Partida).
    - Filtra candidatos por coincidencias con hs_notes y títulos del catálogo.
    - Registra referencias legales (note_id, y si hay, rule_id/legal_source_id vía vínculos).
    """
    cc = ControlConexion()
    steps: List[TraceStep] = []
    try:
        text = ' '.join([t for t in [description] + (extra_texts or []) if t])
        cand = _keyword_candidates(cc, text, limit=100)
        notes, links = _load_notes_links(cc)
        rgi_map = _fetch_rgi_map(cc)

        used_note_ids: List[int] = []
        used_legal_ids: List[int] = []

        # Filtro por notas: si una nota menciona una palabra clave, prioriza capítulos/partidas
        matched_chapters: set[str] = set()
        matched_headings: set[str] = set()

        if not notes.empty and text:
            low = text.lower()
            for _, n in notes.iterrows():
                note_text = str(n.get('text') or '').lower()
                if not note_text:
                    continue
                # Simple heurística: intersección de palabras clave
                hits = 0
                for kw in [w for w in low.split() if len(w) > 3]:
                    if kw in note_text:
                        hits += 1
                        if hits >= 3:
                            break
                if hits >= 3:
                    used_note_ids.append(int(n['id']))
                    scope = str(n.get('scope') or '').upper()
                    scope_code = str(n.get('scope_code') or '')
                    if scope == 'CHAPTER' and scope_code:
                        matched_chapters.add(scope_code.zfill(2)[:2])
                    if scope in ('HEADING', 'PARTIDA') and scope_code:
                        # heading sin punto, e.g., 8471
                        matched_headings.add(scope_code[:4])

        # Reducir candidatos por match de capítulo o partida
        filtered: List[Candidate] = []
        if matched_chapters or matched_headings:
            for c in cand:
                ch = _hs_chapter(c['hs_code'])
                hd = _hs_heading(c['hs_code'])
                if (ch in matched_chapters) or (hd in matched_headings):
                    filtered.append(c)
        else:
            filtered = cand

        # Legal refs adicionales desde links si existen
        if not links.empty and used_note_ids:
            if 'legal_source_id' in links.columns:
                used_legal_ids = list({int(x) for x in links.loc[links['note_id'].isin(used_note_ids)]['legal_source_id'].dropna().tolist()})

        _trace(
            steps,
            'RGI1',
            'Filtrado inicial por textos de partida y Notas legales',
            affected=[c['hs_code'] for c in filtered],
            legal_refs={
                'rgi_id': [rgi_map.get('RGI1')] if rgi_map.get('RGI1') else [],
                'note_id': used_note_ids,
                'legal_source_id': used_legal_ids,
            },
        )
        return filtered, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# RGI 2 -------------------------------------------------------------------
def apply_rgi2(description: str, candidates: List[Candidate], steps: List[TraceStep]) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 2(a) y 2(b) de forma heurística por palabras clave:
    - 2(a): incompleto, desarmado, sin terminar -> tratar como completo si conserva el carácter esencial.
    - 2(b): mezclas, conjuntos, mercancías compuestas.
    En ausencia de estructura de componentes, registra trazabilidad sin filtrar agresivamente.
    """
    cc = ControlConexion()
    try:
        rgi_map = _fetch_rgi_map(cc)
        text = (description or '').lower()
        note_ids: List[int] = []
        decision = []

        incompleto = any(k in text for k in ['incompleto', 'desarmado', 'sin terminar', 'semiarmado'])
        mezcla = any(k in text for k in ['mezcla', 'mixto', 'conjunto', 'set', 'combinado'])

        # Heurística: si es conjunto/mezcla y hay candidatos de distintos capítulos, 
        # preferir el capítulo del título dominantes por mención repetida
        new_cands = candidates[:]
        if mezcla and candidates:
            chapters = {}
            for c in candidates:
                ch = _hs_chapter(c['hs_code'])
                chapters[ch] = chapters.get(ch, 0) + 1
            if chapters:
                dominant = max(chapters.items(), key=lambda x: x[1])[0]
                new_cands = [c for c in candidates if _hs_chapter(c['hs_code']) == dominant]
                decision.append(f"Prioriza capítulo dominante {dominant} (mezcla/conjunto)")

        if incompleto:
            decision.append("Tratar mercancía incompleta/desarmada como completa si conserva carácter esencial")

        _trace(
            steps,
            'RGI2',
            "; ".join(decision) if decision else 'Sin cambios por RGI2',
            affected=[c['hs_code'] for c in new_cands],
            legal_refs={
                'rgi_id': [rgi_map.get('RGI2A'), rgi_map.get('RGI2B')] if (rgi_map.get('RGI2A') or rgi_map.get('RGI2B')) else [],
                'note_id': note_ids,
                'legal_source_id': [],
            },
        )
        return new_cands, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# RGI 3 -------------------------------------------------------------------
def apply_rgi3(candidates: List[Candidate], steps: List[TraceStep]) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 3(a)-(c):
    - 3(a) preferir partida más específica: se aproxima por mayor nivel de detalle (HS6 sobre HS4/HS2) y mejor score.
    - 3(b) carácter esencial: como aproximación, mantener el heading con mayor densidad de candidatos.
    - 3(c) si persiste empate, la última por orden de numeración.
    """
    cc = ControlConexion()
    try:
        rgi_map = _fetch_rgi_map(cc)
        if not candidates:
            _trace(steps, 'RGI3', 'Sin candidatos', [], {'rgi_id': [rgi_map.get('RGI3A'), rgi_map.get('RGI3B'), rgi_map.get('RGI3C')], 'note_id': [], 'legal_source_id': []})
            return candidates, steps

        # 3(a) y 3(b): puntaje por especificidad + densidad por heading
        heading_freq = {}
        for c in candidates:
            hd = _hs_heading(c['hs_code'])
            heading_freq[hd] = heading_freq.get(hd, 0) + 1

        def score(c: Candidate) -> Tuple[int, float, int]:
            hs6_len = 1 if len(_hs6(c['hs_code'])) == 6 else 0
            sc = float(c.get('score') or 0.0)
            dens = heading_freq.get(_hs_heading(c['hs_code']), 0)
            return (hs6_len, sc, dens)

        # Escoge top-N por score para seguir (mantener algunos para RGI6)
        sorted_c = sorted(candidates, key=score, reverse=True)
        top = sorted_c[:10] if len(sorted_c) > 10 else sorted_c

        # 3(c) desempate final: última por numeración
        max_code = max(top, key=lambda c: _hs6(c['hs_code']) or _hs_heading(c['hs_code']) or _hs_chapter(c['hs_code']))
        final_list = [max_code]

        _trace(
            steps,
            'RGI3',
            'Preferencia por especificidad (HS6), densidad por heading y última por numeración como desempate',
            affected=[c['hs_code'] for c in top],
            legal_refs={
                'rgi_id': [rgi_map.get('RGI3A'), rgi_map.get('RGI3B'), rgi_map.get('RGI3C')],
                'note_id': [],
                'legal_source_id': [],
            },
        )
        return final_list, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# RGI 6 -------------------------------------------------------------------
def apply_rgi6(candidates: List[Candidate], steps: List[TraceStep]) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    RGI 6: Comparar únicamente subpartidas del mismo nivel. Si hay más de un HS6
    bajo distintas partidas, restringe al heading de la mejor opción previa.
    """
    cc = ControlConexion()
    try:
        rgi_map = _fetch_rgi_map(cc)
        if not candidates:
            _trace(steps, 'RGI6', 'Sin candidatos', [], {'rgi_id': [rgi_map.get('RGI6')], 'note_id': [], 'legal_source_id': []})
            return candidates, steps

        base = candidates[0]
        base_heading = _hs_heading(base['hs_code'])
        same_heading = [c for c in candidates if _hs_heading(c['hs_code']) == base_heading]
        if same_heading:
            decision = f"Comparación al mismo nivel de subpartida; restringe a heading {base_heading}"
            result = [same_heading[0]]
        else:
            decision = "Sin cambios (ya en el mismo nivel)"
            result = candidates

        _trace(steps, 'RGI6', decision, [c['hs_code'] for c in result], {'rgi_id': [rgi_map.get('RGI6')], 'note_id': [], 'legal_source_id': []})
        return result, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# Orquestador --------------------------------------------------------------
def apply_all(description: str, extra_texts: List[str] | None = None) -> Dict[str, Any]:
    """
    Aplica RGI 1 -> 2 -> 3 -> 6 y retorna un dict con:
    {
        'hs6': '847130',
        'trace': [TraceStep, ...],
        'candidates_final': [Candidate]
    }
    """
    # RGI1: generar y filtrar candidatos
    cand, trace = apply_rgi1(description, extra_texts)

    # RGI2: ajustar por incompletos/mezclas
    cand, trace = apply_rgi2(description, cand, trace)

    # RGI3: resolver empates y especificidad
    cand, trace = apply_rgi3(cand, trace)

    # RGI6: confirmar nivel de comparación
    cand, trace = apply_rgi6(cand, trace)

    hs6 = _hs6(cand[0]['hs_code']) if cand else ''
    return {
        'hs6': hs6,
        'trace': trace,
        'candidates_final': cand,
    }
