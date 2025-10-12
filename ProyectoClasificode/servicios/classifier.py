from typing import Dict, Any, List
import json

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
        
        for opt in options:
            title = str(opt.get('title', '')).lower()
            keywords = str(opt.get('keywords', '')).lower()
            description = str(opt.get('description', '')).lower()
            
            # Combinar todo el texto del item
            item_text = f"{title} {keywords} {description}"
            
            # Calcular score basado en coincidencias de palabras
            score = 0
            text_words = set([w for w in text_lower.split() if len(w) > 2])
            item_words = set([w for w in item_text.split() if len(w) > 2])
            
            # Coincidencias exactas
            exact_matches = text_words.intersection(item_words)
            score += len(exact_matches) * 15
            
            # Coincidencias parciales (substrings)
            for text_word in text_words:
                for item_word in item_words:
                    if text_word in item_word or item_word in text_word:
                        score += 3
            
            # Bonus por categorías específicas
            for category, keywords_list in category_keywords.items():
                text_has_category = any(word in text_lower for word in keywords_list)
                item_has_category = any(word in item_text for word in keywords_list)
                
                if text_has_category and item_has_category:
                    score += 25  # Bonus alto por coincidencia de categoría
            
            # Penalizar items que claramente no coinciden
            if any(word in item_text for word in ['mineral', 'laca', 'colorante', 'manganeso', 'turba']):
                if not any(word in text_lower for word in ['mineral', 'laca', 'colorante', 'manganeso', 'turba']):
                    score -= 50  # Penalización alta
            
            if score > best_score:
                best_score = score
                best_match = opt
        
        # Si encontramos una buena coincidencia por palabras clave, usarla
        if best_match and best_score > 10:
            return best_match
        
        # Si no, intentar con embeddings como respaldo
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
            import numpy as np
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
            return options[0]
            
        except Exception:
            # Si todo falla, usar la primera opción
            return options[0]

    def _try_specific_rules(self, text: str) -> Dict[str, Any]:
        """Intentar aplicar reglas específicas para productos comunes"""
        text_lower = text.lower()
        
        # Buscar coincidencias exactas primero
        for pattern, rule in self.specific_rules.items():
            if pattern in text_lower:
                return rule
        
        # Buscar coincidencias parciales para productos de computación
        if any(word in text_lower for word in ['mouse', 'ratón', 'gaming', 'óptico', 'dpi']):
            if 'mouse' in text_lower or 'ratón' in text_lower:
                return self.specific_rules['mouse gaming']
        
        if any(word in text_lower for word in ['teclado', 'keyboard', 'gaming']):
            if 'teclado' in text_lower or 'keyboard' in text_lower:
                return self.specific_rules['teclado gaming']
        
        if any(word in text_lower for word in ['auriculares', 'headphones', 'gaming']):
            if 'auriculares' in text_lower or 'headphones' in text_lower:
                return self.specific_rules['auriculares gaming']
        
        if any(word in text_lower for word in ['monitor', 'pantalla', 'gaming']):
            if 'monitor' in text_lower or 'pantalla' in text_lower:
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

        # 0) Intentar reglas específicas primero (mejora de precisión)
        specific_result = self._try_specific_rules(text)
        if specific_result:
            # Guardar candidato con regla específica
            try:
                self.candidate_repo.upsert_top1(
                    case['id'],
                    specific_result['hs6'],
                    specific_result['title'],
                    0.95,  # Alta confianza para reglas específicas
                    f"Clasificación por regla específica: {specific_result['title']}",
                    json.dumps({'method': 'specific_rule', 'pattern': 'matched'})
                )
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
                'rationale': 'No hay aperturas nacionales vigentes para el HS6 identificado' if hs6 else 'No se pudo determinar un HS6 con las RGI',
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
            'rationale': self._build_rationale(trace),
        }

    @staticmethod
    def _collect_notes(trace: List[Dict[str, Any]]) -> List[int]:
        note_ids: List[int] = []
        for step in trace:
            for nid in step.get('legal_refs', {}).get('note_id', []) or []:
                if nid not in note_ids:
                    note_ids.append(nid)
        return note_ids

    @staticmethod
    def _collect_sources(trace: List[Dict[str, Any]]) -> List[int]:
        src_ids: List[int] = []
        for step in trace:
            for sid in step.get('legal_refs', {}).get('legal_source_id', []) or []:
                if sid not in src_ids:
                    src_ids.append(sid)
        return src_ids

    @staticmethod
    def _build_rationale(trace: List[Dict[str, Any]]) -> str:
        msgs = []
        for step in trace:
            msgs.append(f"{step.get('rgi')}: {step.get('decision')}")
        return ' | '.join(msgs) if msgs else 'Clasificación basada en RGI y vigencia DIAN'
