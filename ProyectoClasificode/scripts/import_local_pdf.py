#!/usr/bin/env python3
"""
Importador local de un PDF maestro de la DIAN (códigos/notas legales).
Uso:
  python scripts/import_local_pdf.py "C:/ruta/al/archivo.pdf"

Requiere: requests (opcional), pdfminer.six (recomendado para extraer texto).
"""
import sys
import os
import json
from typing import Dict, Any

# Cargar variables de entorno desde .env (opcional)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Asegurar imports relativos al proyecto
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from servicios.scraping.pdf_parser import parse_pdf_or_html
from servicios.scraping.ingestor import DianIngestor
from servicios.scraping.normalizers import to_hs6, to_national10, normalize_title


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_local_pdf.py \"C:/ruta/al/archivo.pdf\"")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.isfile(pdf_path):
        print(f"Archivo no encontrado: {pdf_path}")
        sys.exit(2)

    # Leer bytes localmente
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Parsear como PDF
    parsed = parse_pdf_or_html({'content_type': 'pdf', 'content': pdf_bytes})
    items = parsed.get('items', [])
    raw_text = parsed.get('raw_text', '')

    # Debug: guardar texto crudo para inspección rápida
    try:
        import time
        os.makedirs(os.path.join(BASE_DIR, 'tmp'), exist_ok=True)
        ts = int(time.time())
        txt_path = os.path.join(BASE_DIR, 'tmp', f'parsed_text_{ts}.txt')
        with open(txt_path, 'w', encoding='utf-8') as outf:
            outf.write(raw_text or '')
    except Exception:
        txt_path = None

    # Preparar meta para legal_sources
    fname = os.path.basename(pdf_path)
    meta = {
        'type': 'RESOLUCION',
        'title': fname,
        'url': f'file://{pdf_path}',
    }

    ing = DianIngestor(fetched_by='local_pdf_import')

    # Upsert legal source
    source_id = ing._upsert_legal_source(meta, raw_text, None)

    upserts = 0
    for it in items:
        hs6 = to_hs6(it.get('hs6') or '')
        national = to_national10(it.get('national_code') or '')
        title = normalize_title(it.get('title'))
        vf = it.get('valid_from')
        vt = it.get('valid_to')
        if not hs6 or not national:
            continue
        ok = ing._upsert_tariff_item(hs6, national, title, source_id, vf, vt)
        if ok:
            upserts += 1
            # Recalcular embedding
            try:
                # Obtener id del tariff_item
                q = "SELECT id FROM tariff_items WHERE national_code = :p0"
                df = ing.cc.ejecutar_consulta_sql(q, (national,))
                if df is not None and not df.empty:
                    tid = int(df.iloc[0]['id'])
                    ing._recalc_embedding_for_tariff_item(tid, title)
            except Exception:
                pass

    print(json.dumps({
        'status': 'ok',
        'legal_source_id': source_id,
        'items_parsed': len(items),
        'items_upserted': upserts,
        'debug_text_path': txt_path,
        'file': pdf_path
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
