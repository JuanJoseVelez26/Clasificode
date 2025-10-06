import argparse
import os
import sys
from hashlib import sha256
from typing import List, Dict, Any, Optional, Tuple

# Ensure project root is on PYTHONPATH so we can import 'servicios'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Reuse project services
from servicios.control_conexion import ControlConexion

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None  # Optional dependency; we can still run with plain text


def norm_text(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def hash_text(text: str) -> str:
    return sha256(norm_text(text).encode("utf-8")).hexdigest()


def upsert_hs_note(cc: ControlConexion, scope: str, scope_code: str, note_number: Optional[str], text: str,
                   source_ref: Optional[str] = None) -> Optional[int]:
    """Idempotent upsert for hs_notes using (scope, scope_code, COALESCE(note_number,''), content_hash)."""
    h = hash_text(text)
    sql_insert = (
        """
        INSERT INTO hs_notes(scope, scope_code, note_number, text, content_hash, source_ref, created_at, updated_at)
        VALUES (:p0, :p1, :p2, :p3, :p4, :p5, NOW(), NOW())
        ON CONFLICT (scope, scope_code, COALESCE(note_number,''), content_hash)
        DO NOTHING
        RETURNING id
        """
    )
    inserted_id = cc.ejecutar_comando_sql(sql_insert, (scope, scope_code, note_number or '', text, h, source_ref))
    if inserted_id:
        return int(inserted_id)

    # Check existing latest note for that (scope, scope_code, note_number)
    sql_check = (
        "SELECT id, content_hash FROM hs_notes WHERE scope=:p0 AND scope_code=:p1 AND COALESCE(note_number,'')=:p2 ORDER BY updated_at DESC LIMIT 1"
    )
    df = cc.ejecutar_consulta_sql(sql_check, (scope, scope_code, note_number or ''))
    if df is not None and not df.empty:
        current_id = int(df.iloc[0]["id"])  # type: ignore
        current_hash = str(df.iloc[0]["content_hash"])  # type: ignore
        if current_hash != h:
            sql_update = (
                "UPDATE hs_notes SET text=:p0, content_hash=:p1, updated_at=NOW() WHERE id=:p2"
            )
            cc.ejecutar_comando_sql(sql_update, (text, h, current_id))
        return current_id
    return None


def upsert_rule_link(cc: ControlConexion, rgi: str, hs6: str, note_id: Optional[int] = None, priority: int = 0) -> None:
    sql = (
        """
        INSERT INTO rule_link_hs(rgi, hs6, priority, note_id, created_at, updated_at)
        VALUES(:p0, :p1, :p2, :p3, NOW(), NOW())
        ON CONFLICT (rgi, hs6, COALESCE(note_id,-1))
        DO UPDATE SET priority = EXCLUDED.priority, updated_at = NOW()
        """
    )
    cc.ejecutar_comando_sql(sql, (rgi, hs6, priority, note_id))


# --- Very simple parser scaffold ---
# NOTE: Real parsing depends on the source PDF structure. We provide a pragmatic approach:
# - Split by headings that look like "CAPÍTULO 87" or "SECCIÓN XVI" or HS headings like "8706" at start of line.
# - Everything between headings accumulates as a note.
# You can refine these patterns as needed for your PDF format.

import re

SECTION_RE = re.compile(r"^\s*SECCI[ÓO]N\s+([IVXLCDM]+)\s*$", re.IGNORECASE)
CHAPTER_RE = re.compile(r"^\s*CAP[ÍI]TULO\s+(\d{1,2})\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*(\d{4})\s*$")  # e.g., 8706


def extract_blocks_from_text(text: str) -> List[Dict[str, Any]]:
    lines = [ln.strip() for ln in text.splitlines()]
    blocks: List[Dict[str, Any]] = []
    current_scope: Optional[str] = None
    current_code: Optional[str] = None
    buffer: List[str] = []

    def flush(scope: Optional[str], code: Optional[str], buf: List[str]) -> None:
        if scope and code and buf:
            content = "\n".join(buf).strip()
            if content:
                blocks.append({
                    "scope": scope,
                    "scope_code": code,
                    "note_number": None,
                    "text": content,
                })
        buf.clear()

    for ln in lines:
        m_sec = SECTION_RE.match(ln)
        m_cap = CHAPTER_RE.match(ln)
        m_head = HEADING_RE.match(ln)
        if m_sec:
            # flush previous
            flush(current_scope, current_code, buffer)
            current_scope = "section"
            current_code = m_sec.group(1)
            continue
        if m_cap:
            flush(current_scope, current_code, buffer)
            current_scope = "chapter"
            current_code = m_cap.group(1)
            continue
        if m_head:
            flush(current_scope, current_code, buffer)
            current_scope = "heading"
            current_code = m_head.group(1)
            continue
        buffer.append(ln)

    flush(current_scope, current_code, buffer)
    return blocks


def parse_pdf(pdf_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (notes, links). Links are rudimentary (RGI1 to HS headings seen)."""
    text = ""
    if fitz is not None:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
    else:
        # Fallback: basic read (if the PDF is not text-extractable, user should install PyMuPDF)
        with open(pdf_path, "rb") as f:
            try:
                text = f.read().decode("utf-8", errors="ignore")
            except Exception:
                text = ""
    blocks = extract_blocks_from_text(text)

    notes = blocks
    # Create rudimentary links: for every heading block, associate RGI1 with that HS (HS6 approximated by heading+"00")
    links: List[Dict[str, Any]] = []
    for b in blocks:
        if b["scope"] == "heading" and len(b["scope_code"]) == 4:
            hs6 = b["scope_code"] + "00"  # approximate to HS6
            links.append({
                "rgi": "RGI1",
                "hs6": hs6,
                "note_ref": {"scope": b["scope"], "scope_code": b["scope_code"], "note_number": b.get("note_number")},
                "priority": 0,
            })
    return notes, links


def main():
    parser = argparse.ArgumentParser(description="Incremental import of PDF legal notes & RGI links")
    parser.add_argument("pdf_path", help="Path to source PDF")
    args = parser.parse_args()

    pdf_path = args.pdf_path
    if not os.path.isfile(pdf_path):
        print(f"PDF no encontrado: {pdf_path}")
        return

    cc = ControlConexion()
    notes, links = parse_pdf(pdf_path)

    note_ids: Dict[Tuple[str, str, str], int] = {}
    inserted = 0
    updated = 0

    for n in notes:
        nid = upsert_hs_note(cc, n["scope"], n["scope_code"], n.get("note_number"), n["text"], source_ref=pdf_path)
        if nid:
            note_ids[(n["scope"], n["scope_code"], (n.get("note_number") or ''))] = nid
            inserted += 1

    for l in links:
        note_id = None
        if l.get("note_ref"):
            k = (l["note_ref"]["scope"], l["note_ref"]["scope_code"], (l["note_ref"].get("note_number") or ''))
            note_id = note_ids.get(k)
        upsert_rule_link(cc, l.get("rgi", "RGI1"), l["hs6"], note_id=note_id, priority=int(l.get("priority", 0)))

    print({"notes_processed": len(notes), "links_processed": len(links), "inserted_or_updated_notes": inserted})


if __name__ == "__main__":
    main()
