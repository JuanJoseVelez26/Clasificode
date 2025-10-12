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
    """Búsqueda mejorada por keywords que maneja múltiples términos y sinónimos."""
    text = (text or '').strip().lower()
    if not text:
        return []
    
    # Dividir el texto en palabras individuales (palabras de más de 2 caracteres)
    words = [word.strip() for word in text.split() if len(word.strip()) > 2]
    
    if not words:
        return []
    
    # Mapeo de sinónimos comunes para mejorar la búsqueda
    synonyms = {
        'ternero': ['bovino', 'ganado', 'vaca', 'toro', 'animal', 'bovinos', 'terneros', 'bovino'],
        'vivo': ['animal', 'ganado', 'bovino', 'vivos', 'animales', 'vivo'],
        'camiseta': ['camisa', 'prenda', 'vestido', 'ropa', 'textil', 'camiseta'],
        'algodon': ['algodón', 'textil', 'fibra', 'tela', 'algodon', '100%'],
        'computadora': ['ordenador', 'pc', 'computador', 'equipo', 'computadora'],
        'portatil': ['portátil', 'laptop', 'notebook', 'móvil', 'portatil'],
        'telefono': ['teléfono', 'móvil', 'celular', 'smartphone', 'telefono'],
        'automovil': ['automóvil', 'carro', 'vehículo', 'coche', 'automovil'],
        'motocicleta': ['moto', 'motociclo', 'vehículo', 'motocicleta'],
        'bicicleta': ['bici', 'ciclo', 'vehículo', 'bicicleta'],
        'refrigerador': ['nevera', 'frigorífico', 'heladera', 'refrigerador'],
        'lavadora': ['lavarropas', 'máquina', 'lavadora'],
        'microondas': ['horno', 'microondas'],
        'cafe': ['café', 'grano', 'semilla', 'cafe'],
        'aceite': ['óleo', 'grasa', 'líquido', 'aceite'],
        'chocolate': ['cacao', 'dulce', 'confitería', 'chocolate'],
        'miel': ['abeja', 'dulce', 'natural', 'miel'],
        'vino': ['bebida', 'alcohólico', 'uva', 'vino'],
        'cerveza': ['bebida', 'alcohólico', 'malta', 'cerveza'],
        'cemento': ['construcción', 'material', 'aglomerante', 'cemento'],
        'ladrillo': ['construcción', 'material', 'cerámico', 'ladrillo'],
        'pintura': ['color', 'revestimiento', 'acabado', 'pintura'],
        'taladro': ['herramienta', 'perforar', 'taladrar', 'taladro'],
        'martillo': ['herramienta', 'golpear', 'clavar', 'martillo'],
        'destornillador': ['herramienta', 'atornillar', 'desatornillar', 'destornillador'],
        'bloques': ['construcción', 'juguete', 'piezas', 'bloques'],
        'muñeca': ['juguete', 'niña', 'figura', 'muñeca'],
        'puzzle': ['rompecabezas', 'juego', 'piezas', 'puzzle'],
        'pelota': ['balón', 'esfera', 'juego', 'pelota'],
        'termometro': ['termómetro', 'temperatura', 'medir', 'termometro'],
        'mascarilla': ['máscara', 'protección', 'filtro', 'mascarilla'],
        'guantes': ['manos', 'protección', 'cubrir', 'guantes'],
        'vendaje': ['venda', 'curación', 'herida', 'vendaje'],
        'lapiz': ['lápiz', 'escribir', 'dibujar', 'lapiz'],
        'cuaderno': ['libro', 'escribir', 'papel', 'cuaderno'],
        'boligrafo': ['bolígrafo', 'escribir', 'pluma', 'boligrafo'],
        'pincel': ['pintar', 'brocha', 'arte', 'pincel'],
        'semillas': ['semilla', 'planta', 'germinar', 'semillas'],
        'fertilizante': ['abono', 'nutriente', 'planta', 'fertilizante'],
        'manguera': ['tubo', 'riego', 'agua', 'manguera'],
        'maceta': ['macetero', 'planta', 'jardín', 'maceta'],
        'tijeras': ['cortar', 'podar', 'herramienta', 'tijeras'],
        'reloj': ['tiempo', 'pulsera', 'cronómetro', 'reloj'],
        'perfume': ['fragancia', 'aroma', 'colonia', 'perfume'],
        'collar': ['joya', 'cadena', 'adorno', 'collar'],
        'gafas': ['lentes', 'protección', 'ver', 'gafas'],
        'sierra': ['cortar', 'madera', 'herramienta', 'sierra'],
        'nivel': ['medir', 'horizontal', 'vertical', 'nivel'],
        'multimetro': ['multímetro', 'medir', 'eléctrico', 'multimetro'],
        'mouse': ['ratón', 'mouse', 'periférico', 'dispositivo', 'gaming', 'óptico', 'inalámbrico'],
        'gaming': ['juegos', 'gaming', 'gamer', 'videojuegos', 'entretenimiento'],
        'teclado': ['keyboard', 'teclado', 'periférico', 'dispositivo', 'gaming'],
        'auriculares': ['headphones', 'auriculares', 'audífonos', 'cascos', 'gaming'],
        'monitor': ['pantalla', 'monitor', 'display', 'gaming', 'pantalla'],
        'webcam': ['cámara', 'webcam', 'cámara web', 'videoconferencia'],
        'microfono': ['micrófono', 'microphone', 'mic', 'grabación'],
        'altavoces': ['speakers', 'altavoces', 'parlantes', 'sonido'],
        'impresora': ['printer', 'impresora', 'tinta', 'láser'],
        'escanner': ['scanner', 'escáner', 'digitalización', 'escanear'],
        'tablet': ['tableta', 'tablet', 'ipad', 'android'],
        'smartwatch': ['reloj inteligente', 'smartwatch', 'wearable'],
        'drone': ['dron', 'drone', 'aeronave', 'vuelo'],
        'bateria': ['batería', 'battery', 'pila', 'energía'],
        'cargador': ['charger', 'cargador', 'carga', 'energía'],
        'cable': ['cable', 'wire', 'conexión', 'usb', 'hdmi'],
        'adaptador': ['adapter', 'adaptador', 'conversor', 'conexión']
    }
    
    # Expandir palabras con sinónimos
    expanded_words = set(words)
    for word in words:
        if word in synonyms:
            expanded_words.update(synonyms[word])
    
    # Construir consulta que busque cualquiera de las palabras expandidas
    conditions = []
    params = {}
    
    # Priorizar búsquedas más específicas para productos de computación
    computer_terms = ['mouse', 'ratón', 'gaming', 'teclado', 'keyboard', 'monitor', 'pantalla', 'auriculares', 'headphones']
    has_computer_terms = any(term in text for term in computer_terms)
    
    if has_computer_terms:
        # Buscar específicamente en capítulo 84 (máquinas) y 85 (aparatos eléctricos)
        conditions.append("(chapter = 84 OR chapter = 85)")
    
    for i, word in enumerate(expanded_words):
        param_title = f"word_title_{i}"
        param_keywords = f"word_keywords_{i}"
        conditions.append(f"(LOWER(title) ILIKE :{param_title} OR LOWER(keywords) ILIKE :{param_keywords})")
        params[param_title] = f"%{word}%"
        params[param_keywords] = f"%{word}%"
    
    # Si no hay condiciones, usar búsqueda más amplia
    if not conditions:
        conditions = ["(LOWER(title) ILIKE :text OR LOWER(keywords) ILIKE :text)"]
        params["text"] = f"%{text}%"
    
    query = f"""
        SELECT id, hs_code, title, keywords, level, chapter 
        FROM hs_items 
        WHERE {' AND '.join(conditions) if conditions else '1=1'}
        ORDER BY 
            CASE 
                WHEN LOWER(title) ILIKE :exact_match THEN 1
                WHEN LOWER(keywords) ILIKE :exact_match THEN 2
                ELSE 3
            END,
            CASE 
                WHEN chapter = 84 THEN 1
                WHEN chapter = 85 THEN 2
                ELSE 3
            END,
            hs_code 
        LIMIT :lim
    """
    params["exact_match"] = f"%{text}%"
    params["lim"] = int(limit)
    
    df = _fetch_df(cc, query, params)
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

        # Heurística mejorada: priorizar capítulos más relevantes semánticamente
        new_cands = candidates[:]
        if candidates:
            # Mapeo de palabras clave a capítulos preferidos
            text_lower = text.lower()
            preferred_chapters = []
            
            # Animales vivos (priorizar capítulo 01 para animales vivos)
            if any(word in text_lower for word in ['ternero', 'vivo', 'animal', 'ganado', 'bovino', 'vaca', 'toro']):
                if 'vivo' in text_lower:
                    preferred_chapters.extend([1])  # Solo capítulo 01 para animales vivos
                else:
                    preferred_chapters.extend([1, 2, 3, 4, 5])  # Incluir carne si no especifica "vivo"
            
            # Textiles y prendas
            if any(word in text_lower for word in ['camiseta', 'camisa', 'prenda', 'ropa', 'vestido', 'textil', 'algodón']):
                preferred_chapters.extend([61, 62, 63])
            
            # Máquinas y equipos
            if any(word in text_lower for word in ['computadora', 'máquina', 'equipo', 'motor', 'herramienta']):
                preferred_chapters.extend([84, 85])
            
            # Alimentos
            if any(word in text_lower for word in ['café', 'alimento', 'comida', 'bebida', 'carne']):
                preferred_chapters.extend([16, 17, 18, 19, 20])
            
            # Si hay capítulos preferidos, filtrar por ellos
            if preferred_chapters:
                new_cands = [c for c in candidates if int(_hs_chapter(c['hs_code']) or '0') in preferred_chapters]
                if new_cands:
                    decision.append(f"Prioriza capítulos semánticamente relevantes: {preferred_chapters}")
                else:
                    new_cands = candidates[:]  # Si no hay coincidencias, mantener todos
            elif mezcla and candidates:
                # Lógica original para mezclas sin preferencias semánticas
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

        # 3(a) y 3(b): puntaje por especificidad + densidad por heading + relevancia semántica
        heading_freq = {}
        for c in candidates:
            hd = _hs_heading(c['hs_code'])
            heading_freq[hd] = heading_freq.get(hd, 0) + 1

        def score(c: Candidate) -> Tuple[int, float, int, int]:
            # Priorizar por especificidad (HS6 completo)
            hs6_len = 1 if len(_hs6(c['hs_code'])) == 6 else 0
            # Score original
            sc = float(c.get('score') or 0.0)
            # Densidad por heading
            dens = heading_freq.get(_hs_heading(c['hs_code']), 0)
            # Priorizar capítulos más relevantes (textiles=61-63, animales=01-05, etc.)
            chapter = int(_hs_chapter(c['hs_code']) or '0')
            chapter_priority = 0
            if chapter in [61, 62, 63]:  # Textiles
                chapter_priority = 3
            elif chapter in [1, 2, 3, 4, 5]:  # Animales vivos
                chapter_priority = 3
            elif chapter in [84, 85]:  # Máquinas
                chapter_priority = 2
            elif chapter in [16, 17, 18, 19, 20]:  # Alimentos
                chapter_priority = 2
            else:
                chapter_priority = 1
            
            return (hs6_len, chapter_priority, sc, dens)

        # Escoge top-N por score para seguir (mantener algunos para RGI6)
        sorted_c = sorted(candidates, key=score, reverse=True)
        top = sorted_c[:5] if len(sorted_c) > 5 else sorted_c

        # 3(c) desempate final: última por numeración
        if top:
            max_code = max(top, key=lambda c: _hs6(c['hs_code']) or _hs_heading(c['hs_code']) or _hs_chapter(c['hs_code']))
            final_list = [max_code]
        else:
            final_list = []

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
