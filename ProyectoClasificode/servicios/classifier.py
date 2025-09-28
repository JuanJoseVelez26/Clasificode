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
    """
    def __init__(self):
        self.cc = ControlConexion()
        self.embed = EmbeddingService()
        self.candidate_repo = CandidateRepository()

    def _fetch_tariff_options(self, hs6: str) -> List[Dict[str, Any]]:
        """Obtiene posibles aperturas nacionales vigentes para un HS6."""
        query = (
            "SELECT * FROM v_current_tariff_items "
            "WHERE substring(national_code, 1, 6) = :p0"
        )
        df = self.cc.ejecutar_consulta_sql(query, (hs6,))
        if df.empty:
            return []
        return df.to_dict('records')

    def _select_by_semantics(self, text: str, options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Desempata por similitud semántica usando embeddings de tariff_item, si existen."""
        try:
            # Construir embedding del texto del caso
            qvec = self.embed.generate_embedding(text)
            # Intentar obtener owner_id de las opciones (id de tariff_items)
            ids = [opt.get('id') for opt in options if 'id' in opt]
            if not ids:
                return options[0]

            # Consultar embeddings por owner_type='tariff_item'
            placeholders = ','.join([f":p{i}" for i in range(len(ids))])
            q = (
                "SELECT owner_id, vector FROM embeddings "
                "WHERE owner_type = 'tariff_item' AND owner_id IN (" + placeholders + ")"
            )
            df = self.cc.ejecutar_consulta_sql(q, tuple(ids))
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

            if best is None:
                return options[0]
            for opt in options:
                if int(opt.get('id', -1)) == best:
                    return opt
            return options[0]
        except Exception:
            return options[0]

    def classify(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Clasifica un caso a código nacional de 10 dígitos y guarda candidate(rank=1)."""
        text = f"{case.get('product_title','')} {case.get('product_desc','')}".strip()
        attrs_raw = case.get('attrs_json')
        try:
            attrs = json.loads(attrs_raw) if isinstance(attrs_raw, str) else (attrs_raw or {})
        except Exception:
            attrs = {}

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
