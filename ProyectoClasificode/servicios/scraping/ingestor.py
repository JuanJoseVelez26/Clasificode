import os
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple

from servicios.control_conexion import ControlConexion
from servicios.modeloPln.embedding_service import EmbeddingService
from .dian_scraper import DianiScraper
from .pdf_parser import parse_pdf_or_html
from .normalizers import to_hs6, to_national10, normalize_title


def _log(level: str, msg: str, **kv):
    rec = {"ts": int(time.time()), "level": level, "msg": msg}
    if kv:
        rec.update(kv)
    print(json.dumps(rec, ensure_ascii=False))


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_text(s: str) -> str:
    return _sha256_bytes((s or '').encode('utf-8'))


class DianIngestor:
    """
    Orquestador de scraping e ingesta:
      - Registra corrida en source_sync_runs
      - Recorre resoluciones (DIAN)
      - Inserta/actualiza legal_sources (idempotencia por content_hash)
      - Inserta/actualiza tariff_items (idempotencia por national_code)
      - Recalcula embeddings para tariff_items insertados/actualizados
    """

    def __init__(self, fetched_by: str = 'dian_scraper'):
        self.cc = ControlConexion()
        self.embed = EmbeddingService()
        self.scraper = DianiScraper()
        self.fetched_by = fetched_by
        # Parámetros de entorno
        self.timeout = int(os.getenv('SCRAPER_TIMEOUT_S') or '20')

    # ---------------------------- DB utils ---------------------------------
    def _start_run(self, source_name: str) -> int:
        q = (
            "INSERT INTO source_sync_runs (source_name, status, started_at) "
            "VALUES (:p0, 'running', NOW()) RETURNING id"
        )
        df = self.cc.ejecutar_consulta_sql(q, (source_name,))
        run_id = int(df.iloc[0]['id']) if df is not None and not df.empty else 0
        _log('info', 'sync_run_started', run_id=run_id, source=source_name)
        return run_id

    def _finish_run(self, run_id: int, status: str, items_upserted: int = 0, error: Optional[str] = None):
        q = (
            "UPDATE source_sync_runs SET finished_at = NOW(), status = :p0, items_upserted = :p1, error = :p2 WHERE id = :p3"
        )
        self.cc.ejecutar_comando_sql(q, (status, items_upserted, error, run_id))
        _log('info', 'sync_run_finished', run_id=run_id, status=status, items_upserted=items_upserted, error=error)

    def _upsert_legal_source(self, meta: Dict[str, Any], raw_text: str, raw_bytes: Optional[bytes]) -> int:
        # content_hash para idempotencia (prioriza bytes si existen)
        content_hash = _sha256_bytes(raw_bytes) if raw_bytes else _sha256_text(raw_text)
        # 1) Buscar existente por content_hash
        q_sel = "SELECT id FROM legal_sources WHERE content_hash = :p0 LIMIT 1"
        df = self.cc.ejecutar_consulta_sql(q_sel, (content_hash,))
        if df is not None and not df.empty:
            src_id = int(df.iloc[0]['id'])
            # 2) Actualizar metadata mínima
            q_upd = (
                "UPDATE legal_sources SET updated_at = NOW(), fetched_at = NOW(), summary = :p0, fetched_by = :p1 WHERE id = :p2"
            )
            self.cc.ejecutar_comando_sql(q_upd, (meta.get('title', ''), self.fetched_by, src_id))
            return src_id
        # 3) Insertar nuevo
        q_ins = (
            "INSERT INTO legal_sources (source_type, ref_code, url, fetched_at, content_hash, summary, fetched_by, raw_html, created_at, updated_at) "
            "VALUES (:p0, :p1, :p2, NOW(), :p3, :p4, :p5, :p6, NOW(), NOW()) RETURNING id"
        )
        params = (
            meta.get('type', 'RESOLUCION'),
            meta.get('title', ''),  # usamos ref_code como título/identificador
            meta.get('url'),
            content_hash,
            meta.get('title', ''),
            self.fetched_by,
            raw_bytes if raw_bytes else None,
        )
        df = self.cc.ejecutar_consulta_sql(q_ins, params)
        return int(df.iloc[0]['id']) if df is not None and not df.empty else 0

    def _upsert_hs_item(self, hs6: str, title: Optional[str], keywords: Optional[str], chapter: Optional[int]) -> bool:
        """Crea/actualiza un item HS6 en hs_items. Idempotente por hs_code."""
        if not hs6:
            return False
        q = (
            "INSERT INTO hs_items (hs_code, title, keywords, level, chapter, created_at, updated_at) "
            "VALUES (:p0, :p1, :p2, 6, :p3, NOW(), NOW()) "
            "ON CONFLICT (hs_code) DO UPDATE SET "
            "title = COALESCE(EXCLUDED.title, hs_items.title), "
            "keywords = CONCAT(COALESCE(hs_items.keywords,''),' ',COALESCE(EXCLUDED.keywords,'')), "
            "chapter = COALESCE(EXCLUDED.chapter, hs_items.chapter), "
            "updated_at = NOW()"
        )
        try:
            self.cc.ejecutar_comando_sql(q, (hs6, title or None, (keywords or '').lower(), chapter))
            return True
        except Exception as e:
            _log('warn', 'hs_item_upsert_failed', hs6=hs6, error=str(e))
            return False

    def _upsert_tariff_item(self, hs6: str, national_code: str, title: str, legal_basis_id: int,
                             valid_from: Optional[str], valid_to: Optional[str]) -> bool:
        # Idempotencia por national_code
        q = (
            "INSERT INTO tariff_items (hs6, national_code, title, legal_basis_id, valid_from, valid_to, created_at, updated_at) "
            "VALUES (:p0, :p1, :p2, :p3, :p4, :p5, NOW(), NOW()) "
            "ON CONFLICT (national_code) DO UPDATE SET "
            "title = EXCLUDED.title, legal_basis_id = EXCLUDED.legal_basis_id, valid_from = EXCLUDED.valid_from, valid_to = EXCLUDED.valid_to, updated_at = NOW()"
        )
        try:
            # Validar existencia de legal_basis_id para evitar violar FK
            lbid = legal_basis_id
            try:
                if lbid is not None:
                    df = self.cc.ejecutar_consulta_sql("SELECT 1 FROM legal_sources WHERE id = :p0", (lbid,))
                    if df is None or df.empty:
                        lbid = None
            except Exception:
                lbid = None

            self.cc.ejecutar_comando_sql(q, (hs6, national_code, title, lbid, valid_from, valid_to))
            return True
        except Exception as e:
            _log('error', 'tariff_upsert_failed', national_code=national_code, error=str(e))
            return False

    def _recalc_embedding_for_tariff_item(self, item_id: int, title: str):
        try:
            vector = self.embed.generate_embedding(title)
            # Asegurar vector 1D (no [[...]]). generate_embedding(text) devuelve (1, dim).
            if hasattr(vector, 'shape') and len(vector.shape) == 2 and vector.shape[0] >= 1:
                vec1d = vector[0]
            else:
                vec1d = vector
            # Guardamos el vector como JSON (lista 1D), y en SQL lo convertimos con ::vector
            vector_json = json.dumps(vec1d.tolist() if hasattr(vec1d, 'tolist') else vec1d)
            q = (
                "INSERT INTO embeddings (owner_type, owner_id, provider, model, vector, text_norm, created_at, updated_at) "
                "VALUES ('tariff_item', :p0, :p1, :p2, (:p3)::vector, :p4, NOW(), NOW()) "
                "ON CONFLICT (owner_type, owner_id, provider, model) DO UPDATE SET "
                "vector = EXCLUDED.vector, text_norm = EXCLUDED.text_norm, updated_at = NOW()"
            )
            self.cc.ejecutar_comando_sql(q, (
                item_id, self.embed.provider, self.embed.model, vector_json, title[:1000]
            ))
        except Exception as e:
            _log('warn', 'embedding_upsert_failed', item_id=item_id, error=str(e))

    # ----------------------------- Flow ------------------------------------
    def run(self) -> Dict[str, Any]:
        run_id = self._start_run('DIAN')
        upserts = 0
        try:
            for meta in self.scraper.iter_resolutions():
                url = meta.get('url')
                if not url:
                    continue
                # Descargar contenido (html o pdf url)
                src = self.scraper.fetch_page(url)
                parsed = parse_pdf_or_html(src)
                raw_text = parsed.get('raw_text', '')
                raw_bytes = parsed.get('raw_bytes') if parsed else None
                items = parsed.get('items', [])

                # Registrar/Upsert legal source por content_hash
                legal_source_id = self._upsert_legal_source(meta, raw_text, raw_bytes)

                # Insertar/actualizar cada item en tariff_items
                for it in items:
                    hs6 = to_hs6(it.get('hs6') or '')
                    national = to_national10(it.get('national_code') or '')
                    title = normalize_title(it.get('title'))
                    vf = it.get('valid_from')
                    vt = it.get('valid_to')

                    if not hs6 or not national:
                        continue

                    # Mantener catálogo HS6 base utilizado por RGI
                    try:
                        chapter = int(hs6[:2]) if len(hs6) >= 2 and hs6[:2].isdigit() else None
                        kw = (title or '').lower()
                        self._upsert_hs_item(hs6, title, kw, chapter)
                    except Exception as e:
                        _log('warn', 'hs_item_enrich_failed', hs6=hs6, error=str(e))

                    ok = self._upsert_tariff_item(hs6, national, title, legal_source_id, vf, vt)
                    if ok:
                        upserts += 1
                        # Obtener id del tariff_item recién insertado o existente
                        try:
                            q = "SELECT id FROM tariff_items WHERE national_code = :p0"
                            df = self.cc.ejecutar_consulta_sql(q, (national,))
                            if df is not None and not df.empty:
                                tid = int(df.iloc[0]['id'])
                                self._recalc_embedding_for_tariff_item(tid, title)
                        except Exception as e:
                            _log('warn', 'tariff_lookup_failed', national_code=national, error=str(e))
            self._finish_run(run_id, 'success', items_upserted=upserts, error=None)
            return { 'run_id': run_id, 'status': 'success', 'items_upserted': upserts }
        except Exception as e:
            self._finish_run(run_id, 'failed', items_upserted=upserts, error=str(e))
            return { 'run_id': run_id, 'status': 'failed', 'items_upserted': upserts, 'error': str(e) }
        finally:
            try:
                self.scraper.close()
            except Exception:
                pass
