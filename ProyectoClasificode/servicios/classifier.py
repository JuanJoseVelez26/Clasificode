from typing import Dict, Any, List
import json
import numpy as np
from rapidfuzz import fuzz
import unicodedata
import os

from .control_conexion import ControlConexion
from .modeloPln.embedding_service import EmbeddingService
from .rules.rgi_engine import apply_all as rgi_apply_all
from .repos import CandidateRepository


class NationalClassifier:
    """
    Clasificador para bajar de HS6 a código nacional de 10 dígitos usando:
    - Vista v_current_tariff_items (vigencia)
    - attrs_json del caso para desambiguación
    - Similitud semántica con embeddings owner_type='tariff_item' como desempate
    - Reglas específicas para productos comunes
    """
    def __init__(self):
        self.cc = ControlConexion()
        self.embed = EmbeddingService()
        self.candidate_repo = CandidateRepository()
        
        # Reglas específicas para productos comunes (mejora de precisión)
        self.specific_rules = {
            'computadora portatil': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'camiseta algodon': {'hs6': '610910', 'national_code': '6109100000', 'title': 'Camisetas de algodón'},
            'ternero vivo': {'hs6': '010290', 'national_code': '0102900000', 'title': 'Animales vivos de la especie bovina'},
            'cafe grano': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'smartphone': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'automovil': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'refrigerador': {'hs6': '841810', 'national_code': '8418100000', 'title': 'Refrigeradores y congeladores combinados'},
            'mouse gaming': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'mouse optico': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'raton gaming': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'teclado gaming': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'auriculares gaming': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'monitor gaming': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
        }

    def _fetch_tariff_options(self, hs6: str) -> List[Dict[str, Any]]:
        """Obtiene posibles aperturas nacionales vigentes para un HS6."""
        query = (
            "SELECT * FROM v_current_tariff_items "
            "WHERE substring(national_code, 1, 6) = :hs6"
        )
        df = self.cc.ejecutar_consulta_sql(query, {"hs6": hs6})
        if df.empty:
            return []
        return df.to_dict('records')

    def _select_by_semantics(self, text: str, options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Selecciona la opción más semánticamente similar usando palabras clave mejoradas."""
        if not options:
            return {}
        
        # Primero intentar selección por palabras clave mejorada
        text_lower = text.lower()
        best_match = None
        best_score = 0
        
        # Mapeo de palabras clave a categorías específicas
        category_keywords = {
            'textiles': ['camiseta', 'camisa', 'prenda', 'ropa', 'vestido', 'textil', 'algodón', 'gorra', 'sombrero', 'pantalón', 'falda'],
            'computadoras': ['computadora', 'portátil', 'laptop', 'ordenador', 'equipo', 'pc', 'notebook'],
            'alimentos': ['café', 'grano', 'semilla', 'tostado', 'alimento', 'comida', 'bebida'],
            'vehiculos': ['automóvil', 'carro', 'vehículo', 'coche', 'moto', 'bicicleta'],
            'electrodomesticos': ['refrigerador', 'nevera', 'frigorífico', 'lavadora', 'microondas', 'aire acondicionado'],
            'herramientas': ['taladro', 'martillo', 'destornillador', 'herramienta', 'sierra'],
            'animales': ['ternero', 'vivo', 'animal', 'ganado', 'bovino', 'vaca', 'toro']
        }
        
        # Pre-calcular embedding del texto del caso
        try:
            qvec = np.array(self.embed.generate_embedding(text))
        except Exception:
            qvec = None

        # Inferir dominio del texto para sesgos controlados
        domain = self._infer_domain(text_lower)

        # Pre-cargar embeddings existentes para las opciones (owner_type=tariff_item)
        option_ids = [int(o.get('id')) for o in options if o.get('id') is not None]
        emb_map: Dict[int, np.ndarray] = {}
        if option_ids:
            try:
                in_clause = '(' + ','.join([str(i) for i in option_ids]) + ')'
                q = (
                    "SELECT owner_id, vector FROM embeddings "
                    "WHERE owner_type = 'tariff_item' AND owner_id IN " + in_clause
                )
                df_emb = self.cc.ejecutar_consulta_sql(q)
                for _, row in df_emb.iterrows():
                    vec_str = row['vector']
                    try:
                        emb_map[int(row['owner_id'])] = np.array(json.loads(vec_str))
                    except Exception:
                        s = str(vec_str).strip().strip('[]{}')
                        parts = [p for p in s.replace('{','').replace('}','').split(',') if p.strip()]
                        emb_map[int(row['owner_id'])] = np.array([float(p) for p in parts]) if parts else None
            except Exception:
                emb_map = {}

        # Recorrer opciones y calcular puntajes combinados
        scores: List[Dict[str, Any]] = []
        for opt in options:
            title = str(opt.get('title', '')).lower()
            keywords = str(opt.get('keywords', '')).lower()
            description = str(opt.get('description', '')).lower()
            item_text = f"{title} {keywords} {description}".strip()

            # 1) Puntaje léxico con RapidFuzz (0..100)
            lex_score = fuzz.token_set_ratio(text_lower, item_text)  # 0..100
            lex_norm = lex_score / 100.0

            # 2) Bonus por categorías específicas
            cat_bonus = 0.0
            for _, keywords_list in category_keywords.items():
                text_has_category = any(word in text_lower for word in keywords_list)
                item_has_category = any(word in item_text for word in keywords_list)
                if text_has_category and item_has_category:
                    cat_bonus += 0.1  # bonus pequeño acumulable

            # 3) Puntaje semántico si hay embeddings para el item
            sem_norm = 0.0
            if qvec is not None:
                v = emb_map.get(int(opt.get('id', -1)))
                if v is not None and v.size > 0:
                    denom = (np.linalg.norm(qvec) * np.linalg.norm(v))
                    if denom:
                        sim = float(np.dot(qvec, v) / denom)  # -1..1
                        sem_norm = (sim + 1.0) / 2.0          # 0..1

            # 4) Penalización por palabras claramente ajenas (evitar minerales para ropa, etc.)
            negative_words = ['mineral', 'minerales', 'manganeso', 'mena', 'concentrado', 'turba', 'colorante industrial']
            neg_penalty = 0.0
            if any(w in item_text for w in negative_words) and not any(w in text_lower for w in negative_words):
                neg_penalty = 0.25  # resta al score final

            # 5) Señal full-text (ts_rank) sobre tariff_items sin cambiar la BD (on-the-fly)
            ft_norm = 0.0
            try:
                oid = int(opt.get('id', -1))
                if oid != -1:
                    q = (
                        "SELECT id, ts_rank_cd("
                        "to_tsvector('spanish', coalesce(title,'')||' '||coalesce(keywords,'')||' '||coalesce(notes,'')),"
                        "plainto_tsquery('spanish', :q)) AS r FROM tariff_items WHERE id = :oid"
                    )
                    df_rank = self.cc.ejecutar_consulta_sql(q, {"q": text, "oid": oid})
                    if not df_rank.empty:
                        r = float(df_rank.iloc[0]['r'] or 0.0)
                        # Normalización tosca: ts_rank suele ~[0..1]
                        ft_norm = max(0.0, min(1.0, r))
            except Exception:
                ft_norm = 0.0

            # 6) Score combinado (pesos ajustables)
            w_sem = float(os.getenv('CLS_W_SEM', '0.45'))
            w_lex = float(os.getenv('CLS_W_LEX', '0.35'))
            w_cat = float(os.getenv('CLS_W_CAT', '0.20'))
            w_ft = float(os.getenv('CLS_W_FT', '0.35'))
            # Rebalancear manteniendo suma aprox. 1: combinar ft con los otros pesos proporcionalmente
            score = (w_sem * sem_norm + w_lex * lex_norm + w_cat * max(0.0, min(1.0, cat_bonus)) + w_ft * ft_norm) - neg_penalty

            # 6) Sesgo por dominio usando prefijos de capítulos de national_code/hs6
            code_digits = ''.join([c for c in str(opt.get('national_code') or '') if c.isdigit()])
            if len(code_digits) < 2:
                code_digits = ''.join([c for c in str(opt.get('hs6') or '') if c.isdigit()])
            ch = code_digits[:2] if len(code_digits) >= 2 else ''
            boost = float(os.getenv('CLS_W_DOMAIN_BOOST', '0.1'))
            boost_e = float(os.getenv('CLS_W_DOMAIN_BOOST_E', '0.08'))
            boost_m = float(os.getenv('CLS_W_DOMAIN_BOOST_M', '0.06'))
            boost_min = float(os.getenv('CLS_W_DOMAIN_BOOST_MIN', '0.08'))
            if domain == 'textiles' and ch in ('61', '62'):
                score += boost
            elif domain == 'vehiculos' and ch == '87':
                score += boost
            elif domain == 'electronicos' and ch in ('84','85'):
                score += boost_e
            elif domain == 'medico' and ch in ('30','90'):
                score += boost_m
            elif domain == 'minerales' and ch in ('25','26','27'):
                score += boost_min
            elif domain == 'herramientas' and ch == '82':
                score += boost
            elif domain == 'calzado' and ch == '64':
                score += boost

            opt_scored = dict(opt)
            opt_scored['_score'] = float(score)
            scores.append(opt_scored)
            if score > best_score:
                best_score = score
                best_match = opt
        
        # Si encontramos una buena coincidencia por palabras clave, usarla
        if best_match and best_score > 10:
            # Attach ranked list for later (top-3)
            scores_sorted = sorted(scores, key=lambda o: o.get('_score', 0.0), reverse=True)
            self._last_ranked_options = scores_sorted[:3]
            return best_match
        
        # Si no, intentar con embeddings/lexical como respaldo adicional (fallback antiguo)
        try:
            # Construir embedding del texto del caso
            qvec = self.embed.generate_embedding(text)
            # Derivar hs6 desde las opciones (todas comparten mismo hs6)
            hs6 = None
            for opt in options:
                nc = str(opt.get('national_code') or '')
                digits = ''.join([c for c in nc if c.isdigit()])
                if len(digits) >= 6:
                    hs6 = digits[:6]
                    break
            if not hs6:
                return options[0]

            # Consultar embeddings de hs_items para ese HS6
            q = (
                "SELECT ev.owner_id, ev.vector "
                "FROM embeddings ev JOIN hs_items hi ON hi.id = ev.owner_id "
                "WHERE ev.owner_type = 'hs_item' AND replace(hi.hs_code, '.', '') LIKE :hs6pref"
            )
            df = self.cc.ejecutar_consulta_sql(q, {"hs6pref": f"{hs6}%"})
            if df.empty:
                return options[0]

            # Convertir a vectores numpy
            best = None
            best_sim = -1e9
            # qvec puede venir como np.ndarray shape (1,dim) según servicio
            q = qvec[0] if hasattr(qvec, 'shape') and len(qvec.shape) == 2 else qvec
            for _, row in df.iterrows():
                vec_str = row['vector']
                # vector se almacena como '[]' json o formato vector pgvector en nuestro código guardamos como ::vector desde json
                try:
                    # Intentar JSON primero
                    v = np.array(json.loads(vec_str))
                except Exception:
                    # Fallback: parseo simple de '{...}' o formato pgvector no json
                    s = str(vec_str).strip().strip('[]{}')
                    parts = [p for p in s.replace('{','').replace('}','').split(',') if p.strip()]
                    v = np.array([float(p) for p in parts]) if parts else None
                if v is None or v.size == 0:
                    continue
                # similitud coseno
                denom = (np.linalg.norm(q) * np.linalg.norm(v))
                sim = float(np.dot(q, v) / denom) if denom else -1e9
                if sim > best_sim:
                    best_sim = sim
                    best = int(row['owner_id'])

            if best is not None:
                for opt in options:
                    if int(opt.get('id', -1)) == best:
                        return opt
            
            # Si los embeddings fallan, usar la primera opción
            scores_sorted = sorted(scores, key=lambda o: o.get('_score', 0.0), reverse=True)
            self._last_ranked_options = scores_sorted[:3]
            return options[0]
            
        except Exception:
            # Si todo falla, usar la primera opción
            scores_sorted = sorted(scores, key=lambda o: o.get('_score', 0.0), reverse=True)
            self._last_ranked_options = scores_sorted[:3] if scores_sorted else []
            return options[0]

    def _try_specific_rules(self, text: str) -> Dict[str, Any]:
        """Intentar aplicar reglas específicas para productos comunes"""
        def _norm(s: str) -> str:
            s = s.lower()
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            for ch in [',', '.', ';', ':', '(', ')', '[', ']', '{', '}', '/', '\\', '-', '_']:
                s = s.replace(ch, ' ')
            s = ' '.join(s.split())
            return s

        text_norm = _norm(text)
        
        # Reglas y sinónimos para camiseta de algodón
        synonyms = [
            'camiseta algodon', 'camiseta de algodon', 'camiseta 100 algodon', 'playera algodon',
            'remera algodon', 'polera algodon', 'tshirt algodon', 't shirt algodon'
        ]
        for patt in synonyms:
            if patt in text_norm:
                return self.specific_rules.get('camiseta algodon')

        # Buscar coincidencias exactas de patrones existentes (normalizados)
        for pattern, rule in self.specific_rules.items():
            if _norm(pattern) in text_norm:
                return rule
        
        # Buscar coincidencias parciales para productos de computación
        if any(word in text_norm for word in ['mouse', 'raton', 'gaming', 'optico', 'dpi']):
            if 'mouse' in text_norm or 'raton' in text_norm:
                return self.specific_rules['mouse gaming']
        
        if any(word in text_norm for word in ['teclado', 'keyboard', 'gaming']):
            if 'teclado' in text_norm or 'keyboard' in text_norm:
                return self.specific_rules['teclado gaming']
        
        if any(word in text_norm for word in ['auriculares', 'headphones', 'gaming']):
            if 'auriculares' in text_norm or 'headphones' in text_norm:
                return self.specific_rules['auriculares gaming']
        
        if any(word in text_norm for word in ['monitor', 'pantalla', 'gaming']):
            if 'monitor' in text_norm or 'pantalla' in text_norm:
                return self.specific_rules['monitor gaming']
        
        return None

    def classify(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Clasifica un caso a código nacional de 10 dígitos y guarda candidate(rank=1)."""
        text = f"{case.get('product_title','')} {case.get('product_desc','')}".strip()
        attrs_raw = case.get('attrs_json')
        try:
            attrs = json.loads(attrs_raw) if isinstance(attrs_raw, str) else (attrs_raw or {})
        except Exception:
            attrs = {}
        
        # Preprocesar y normalizar texto
        text = self._preprocess_text(text)
        
        # Extraer características para explicación
        features = self._extract_features(text)

        # 0) Intentar reglas específicas primero (mejora de precisión)
        specific_result = self._try_specific_rules(text)
        if specific_result:
            # Guardar candidato con regla específica
            try:
                rationale = f"Clasificación por regla específica: {specific_result['title']}"
                self.candidate_repo.create_candidates_batch([
                    {
                        'case_id': case['id'],
                        'hs_code': specific_result['national_code'] or specific_result['hs6'],
                        'hs6': specific_result['hs6'],
                        'national_code': specific_result['national_code'],
                        'title': specific_result['title'],
                        'confidence': 0.95,
                        'rationale': rationale,
                        'legal_refs_json': json.dumps({'method': 'specific_rule', 'pattern': 'matched'}),
                        'rank': 1,
                    }
                ])
            except Exception as e:
                print(f"Error guardando candidato: {e}")
                # Continuar sin fallar si no se puede guardar
            
            return {
                'case_id': case['id'],
                'hs6': specific_result['hs6'],
                'national_code': specific_result['national_code'],
                'title': specific_result['title'],
                'rgi_applied': ['Regla específica'],
                'legal_notes': [],
                'sources': [],
                'rationale': f"Clasificación por regla específica para productos comunes: {specific_result['title']}",
            }

        # 1) Ejecutar motor RGI -> HS6 + trazabilidad
        rgi_result = rgi_apply_all(text, [])
        hs6 = rgi_result.get('hs6')
        trace = rgi_result.get('trace', [])

        # Fallback HS6 si RGI no lo determinó
        if not hs6:
            hs6 = self._fallback_hs6(text)

        # 2) Obtener aperturas nacionales vigentes
        options = self._fetch_tariff_options(hs6) if hs6 else []
        if not options:
            return {
                'case_id': case['id'],
                'hs6': hs6 or '',
                'national_code': '',
                'title': '',
                'rgi_applied': [s.get('rgi') for s in trace],
                'legal_notes': self._collect_notes(trace),
                'sources': self._collect_sources(trace),
                'rationale': (("Identificación: " + str(features) + " | ") if features else '') + ('No hay aperturas nacionales vigentes para el HS6 identificado' if hs6 else 'No se pudo determinar un HS6 (RGI + fallback)'),
                'analysis': {'features': features},
            }

        # 3) Seleccionar exactamente un national_code
        # Heurística simple con attrs: priorizar por title/keywords si coincide con alguna clave del attrs
        chosen = None
        if attrs and options:
            attrs_text = ' '.join([str(v) for v in attrs.values() if v is not None]).lower()
            for opt in options:
                line = ' '.join([str(opt.get('title','')), str(opt.get('keywords','')), str(opt.get('notes',''))]).lower()
                # Si hay intersección mínima de términos, elegir
                hits = 0
                for token in set([t for t in attrs_text.split() if len(t) > 3]):
                    if token in line:
                        hits += 1
                        if hits >= 2:
                            chosen = opt
                            break
                if chosen:
                    break

        # Si sigue sin elegirse, usar similitud semántica con embeddings
        if chosen is None:
            chosen = self._select_by_semantics(text, options)

        national_code = str(chosen.get('national_code', '')).strip()
        title = chosen.get('title') or chosen.get('description') or ''

        # 4) Guardar candidate rank=1
        try:
            rationale = self._build_rationale(trace)
            self.candidate_repo.create_candidates_batch([
                {
                    'case_id': case['id'],
                    'hs_code': national_code or hs6 or '',
                    'title': title or 'Tariff item',
                    'confidence': 0.95 if national_code else 0.7,
                    'rationale': rationale,
                    'legal_refs_json': json.dumps({
                        'rgi_applied': [s.get('rgi') for s in trace],
                        'trace': trace,
                    }),
                    'rank': 1,
                }
            ])
        except Exception:
            pass

        return {
            'case_id': case['id'],
            'hs6': hs6,
            'national_code': national_code,
            'title': title,
            'rgi_applied': [s.get('rgi') for s in trace],
            'legal_notes': self._collect_notes(trace),
            'sources': self._collect_sources(trace),
            'rationale': (("Identificación: " + str(features) + " | ") if features else '') + self._build_rationale(trace),
            'analysis': {'features': features},
        }

    def _fallback_hs6(self, text: str) -> str:
        """Intentar proponer un HS6 cuando RGI no lo determinó, combinando búsqueda léxica y semántica sobre hs_items."""
        try:
            # 1) Recuperar candidatos hs_items filtrando por tokens relevantes para limitar el set
            tokens = [t for t in set(text.lower().replace(',', ' ').split()) if len(t) > 3]
            like_filters = ' OR '.join([f"title ILIKE '%{t}%'" for t in tokens[:6]])
            base_q = "SELECT id, hs_code, title, keywords FROM hs_items"
            q = base_q + (f" WHERE {like_filters} LIMIT 200" if like_filters else " LIMIT 200")
            df = self.cc.ejecutar_consulta_sql(q)
            if df.empty:
                return ''

            # 2) Pre-calcular embedding del texto
            try:
                qvec = np.array(self.embed.generate_embedding(text))
            except Exception:
                qvec = None

            # 3) Traer embeddings para hs_items candidatos
            emb_map = {}
            try:
                ids = [int(r['id']) for _, r in df.iterrows() if r.get('id') is not None]
                if ids:
                    in_clause = '(' + ','.join([str(i) for i in ids]) + ')'
                    qe = (
                        "SELECT owner_id, vector FROM embeddings "
                        "WHERE owner_type='hs_item' AND owner_id IN " + in_clause
                    )
                    df_emb = self.cc.ejecutar_consulta_sql(qe)
                    for _, row in df_emb.iterrows():
                        vec_str = row['vector']
                        try:
                            emb_map[int(row['owner_id'])] = np.array(json.loads(vec_str))
                        except Exception:
                            s = str(vec_str).strip().strip('[]{}')
                            parts = [p for p in s.replace('{','').replace('}','').split(',') if p.strip()]
                            emb_map[int(row['owner_id'])] = np.array([float(p) for p in parts]) if parts else None
            except Exception:
                emb_map = {}

            # 4) Calcular score combinado (semántico + léxico) y elegir mejor hs6, con sesgo por dominio
            garment_terms = ['chaqueta', 'abrigo', 'parka', 'anorak', 'cazadora', 'impermeable', 'prenda', 'ropa', 'sobretodo', 'saco']
            garment_intent = any(t in text.lower() for t in garment_terms)
            domain = self._infer_domain(text.lower())

            best_hs6 = ''
            best_score = -1.0
            for _, row in df.iterrows():
                item_text = f"{str(row.get('title') or '')} {str(row.get('keywords') or '')}"
                lex = fuzz.token_set_ratio(text, item_text) / 100.0
                sem = 0.0
                if qvec is not None:
                    v = emb_map.get(int(row['id']))
                    if v is not None and v.size > 0:
                        denom = (np.linalg.norm(qvec) * np.linalg.norm(v))
                        if denom:
                            sim = float(np.dot(qvec, v) / denom)
                            sem = (sim + 1.0) / 2.0
                w_sem_fb = float(os.getenv('CLS_FB_W_SEM', '0.6'))
                w_lex_fb = float(os.getenv('CLS_FB_W_LEX', '0.4'))
                score = w_sem_fb * sem + w_lex_fb * lex

                # Ajuste por dominio prendas de vestir
                hs = ''.join([c for c in str(row.get('hs_code') or '') if c.isdigit()])
                ch = hs[:2] if len(hs) >= 2 else ''
                if garment_intent or domain == 'textiles':
                    if ch in ('61', '62'):
                        score += float(os.getenv('CLS_W_GARMENT_BOOST', '0.15'))  # boost por capítulo de prendas
                    elif ch in ('05', '67'):
                        score -= float(os.getenv('CLS_W_GARMENT_PENALTY', '0.25'))  # penalización por materias primas (plumas)
                elif domain == 'vehiculos':
                    if ch == '87':
                        score += float(os.getenv('CLS_W_DOM_VEH', '0.12'))
                elif domain == 'electronicos':
                    if ch in ('84','85'):
                        score += float(os.getenv('CLS_W_DOM_ELEC', '0.10'))
                elif domain == 'minerales':
                    if ch in ('25','26','27'):
                        score += float(os.getenv('CLS_W_DOM_MIN', '0.10'))
                elif domain == 'herramientas':
                    if ch == '82':
                        score += float(os.getenv('CLS_W_DOM_TOOL', '0.12'))
                elif domain == 'calzado':
                    if ch == '64':
                        score += float(os.getenv('CLS_W_DOM_SHOE', '0.12'))

                if score > best_score:
                    hs6 = hs[:6] if len(hs) >= 6 else ''
                    if hs6:
                        best_score = score
                        best_hs6 = hs6

            return best_hs6
        except Exception:
            return ''

    @staticmethod
    def _collect_notes(trace: List[Dict[str, Any]]) -> List[int]:
        note_ids: List[int] = []
        for step in trace:
            for nid in step.get('legal_refs', {}).get('note_id', []) or []:
                if nid not in note_ids:
                    note_ids.append(nid)
        return note_ids

    @staticmethod
    def _collect_sources(trace: List[Dict[str, Any]]) -> List[str]:
        srcs: List[str] = []
        for step in trace:
            for s in step.get('sources', []) or []:
                if s not in srcs:
                    srcs.append(s)
        return srcs

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """Normaliza y limpia el texto de entrada."""
        if not text:
            return ''
        # Convertir a minúsculas
        text = text.lower()
        # Normalizar espacios múltiples
        text = ' '.join(text.split())
        # Remover caracteres extraños pero mantener acentos y ñ
        import re as _re
        text = _re.sub(r'[^a-záéíóúüñ\s\d\.,%-]', ' ', text)
        text = ' '.join(text.split())
        return text
    
    @staticmethod
    def _infer_domain(text_lower: str) -> str:
        """Inferir un dominio general a partir del texto para aplicar sesgos suaves.
        Dominios: textiles, vehiculos, electronicos, medico, minerales, alimentos.
        """
        groups = {
            'textiles': ['camiseta','camisa','pantalon','chaqueta','abrigo','prenda','ropa','algodon','poliester','lana','tejido','cuero','zapato','bolso','gorra','plumas','impermeable'],
            'vehiculos': ['automovil','carro','vehiculo','moto','motocicleta','bicicleta','camion','bus','neumatico','llanta','chasis'],
            'electronicos': ['monitor','teclado','mouse','consola','led','bateria','refrigerador','lavadora','microondas','acondicionado','aspiradora','licuadora','plancha','sensor'],
            'medico': ['tensiometro','termometro','oximetro','mascarilla','guantes','vendaje','quirurgico','clinico'],
            'minerales': ['mineral','mena','concentrado','manganeso','hierro','cobre','turba','carbon'],
            'alimentos': ['cafe','azucar','harina','bebida','alimento','chocolate','leche'],
            'herramientas': ['martillo','taladro','destornillador','llave inglesa','sierra','cinta metrica','cuchillo','alicate'],
            'calzado': ['zapato','zapatilla','tenis','botin','bota','calzado','sandalia','deportivo','suela','antideslizante','malla']
        }
        for dom, kws in groups.items():
            if any(k in text_lower for k in kws):
                return dom
        return ''

    @staticmethod
    def _build_rationale(trace: List[Dict[str, Any]]) -> str:
        msgs = []
        for step in trace:
            msgs.append(f"{step.get('rgi')}: {step.get('decision')}")
        return ' | '.join(msgs) if msgs else 'Clasificación basada en RGI y vigencia DIAN'

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """Normaliza y limpia el texto de entrada."""
        if not text:
            return ''
        # Convertir a minúsculas
        text = text.lower()
        # Normalizar espacios múltiples
        text = ' '.join(text.split())
        # Remover caracteres extraños pero mantener acentos y ñ
        import re as _re
        text = _re.sub(r'[^a-záéíóúüñ\s\d\.,%-]', ' ', text)
        text = ' '.join(text.split())
        return text

    @staticmethod
    def _extract_features(text: str) -> Dict[str, Any]:
        """Extrae características clave del texto: tipo, materiales, medidas, uso."""
        import re as _re
        t = (text or '').lower()
        # Normalizar acentos
        t_norm = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
        feats: Dict[str, Any] = {}
        
        # 1. Materiales
        mats = []
        mat_kws = ['acero','aluminio','madera','plastico','algodon','poliester','cuero','vidrio','caucho','goma','sintetico','malla','textil','ceramica','hierro','cobre']
        for m in mat_kws:
            if m in t_norm:
                mats.append(m)
        if mats:
            feats['material'] = ','.join(mats)
        
        # 2. Tipo de producto (palabras clave)
        tipo_kws = [
            'martillo','taladro','destornillador','chaqueta','camiseta','pantalon','zapato','zapatilla','tenis','calzado',
            'refrigerador','lavadora','microondas','bateria','faro','neumatico','filtro','aceite','bujia','bomba',
            'cafe','chocolate','miel','cerveza','vino','aceite','cemento','ladrillo'
        ]
        for kw in tipo_kws:
            if kw in t_norm:
                feats['tipo'] = kw
                break
        
        # 3. Medidas y unidades
        medidas = _re.findall(r"(\d+(?:[\.\,]\d+)?)(?:\s*)(kg|g|l|ml|mm|cm|m|btu|w|kw|v|ah|cc|pulgadas)", t_norm)
        if medidas:
            feats['medidas'] = [f"{m[0]}{m[1]}" for m in medidas]
        
        # 4. Uso/función
        uso_kws = ['deportivo','industrial','medico','construccion','carpintero','cocina','hogar','automotriz','infantil']
        for u in uso_kws:
            if u in t_norm:
                feats['uso'] = u
                break
        
        # 5. Partes vs. completo (RGI 2a)
        if any(w in t_norm for w in ['parte','repuesto','componente','accesorio']):
            feats['es_parte'] = True
        
        return feats
