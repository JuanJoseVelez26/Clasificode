-- db.sql
-- Clasificode database schema and seed
-- Compatible con PostgreSQL + pgvector + pgcrypto
-- Embeddings fijos en text-embedding-3-small (dim=1536)

-- 0) Extensiones
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- bcrypt via crypt()/gen_salt('bf')
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector

-- 1) Tablas

-- 1.1 users
CREATE TABLE IF NOT EXISTS users (
  id            BIGSERIAL PRIMARY KEY,
  email         VARCHAR(320) NOT NULL UNIQUE,
  password_hash VARCHAR(200) NOT NULL,
  name          VARCHAR(200) NOT NULL,
  role          VARCHAR(32)  NOT NULL DEFAULT 'operator',
  is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 1.2 legal_sources
CREATE TABLE IF NOT EXISTS legal_sources (
  id            BIGSERIAL PRIMARY KEY,
  source_type   VARCHAR(50) NOT NULL,           -- RESOLUCION, RGI, MANUAL
  ref_code      VARCHAR(200),
  url           TEXT,
  fetched_at    TIMESTAMPTZ,
  content_hash  VARCHAR(128) UNIQUE,
  summary       TEXT,
  fetched_by    VARCHAR(100),
  raw_html      BYTEA,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_legal_sources_ref ON legal_sources(ref_code);

CREATE TABLE IF NOT EXISTS tariff_items (
  id             BIGSERIAL PRIMARY KEY,
  hs6            VARCHAR(6)  NOT NULL,            -- prefijo HS6 (e.g., 871200)
  national_code  VARCHAR(10) NOT NULL,            -- 10 dígitos, sin puntos
  title          TEXT        NOT NULL,
  keywords       TEXT,
  notes          TEXT,
  legal_basis_id BIGINT      REFERENCES legal_sources(id) ON DELETE SET NULL,
  active         BOOLEAN     NOT NULL DEFAULT TRUE,
  valid_from     DATE,
  valid_to       DATE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (national_code)
);
-- Compatibilidad con esquemas previos: si existe hs_code6, migrar a hs6
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tariff_items' AND column_name = 'hs_code6'
  ) THEN
    ALTER TABLE tariff_items ADD COLUMN IF NOT EXISTS hs6 VARCHAR(6);
    UPDATE tariff_items SET hs6 = COALESCE(hs6, hs_code6) WHERE hs6 IS NULL AND hs_code6 IS NOT NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tariff_items_hs6 ON tariff_items(hs6);
CREATE INDEX IF NOT EXISTS idx_tariff_items_ncode ON tariff_items(national_code);
CREATE INDEX IF NOT EXISTS idx_tariff_items_valid ON tariff_items(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_tariff_items_active ON tariff_items(active);

-- 1.4 embeddings (solo text-embedding-3-small, dim=1536)
CREATE TABLE IF NOT EXISTS embeddings (
  id          BIGSERIAL PRIMARY KEY,
  owner_type  VARCHAR(50)  NOT NULL,            -- 'tariff_item', 'case', etc.
  owner_id    BIGINT       NOT NULL,
  provider    VARCHAR(50)  NOT NULL DEFAULT 'openai',
  model       VARCHAR(200) NOT NULL DEFAULT 'text-embedding-3-small',
  vector      vector(1536) NOT NULL,            -- dimensión fija
  text_norm   TEXT,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  UNIQUE (owner_type, owner_id, provider, model)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_owner ON embeddings(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine
  ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- 1.5 source_sync_runs
CREATE TABLE IF NOT EXISTS source_sync_runs (
  id              BIGSERIAL PRIMARY KEY,
  source_name     VARCHAR(100) NOT NULL,
  status          VARCHAR(30)  NOT NULL,
  started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  finished_at     TIMESTAMPTZ,
  items_upserted  INTEGER      NOT NULL DEFAULT 0,
  error           TEXT
);

-- 1.6 hs_items
CREATE TABLE IF NOT EXISTS hs_items (
  id          BIGSERIAL PRIMARY KEY,
  hs_code     VARCHAR(20) NOT NULL UNIQUE,
  title       TEXT        NOT NULL,
  keywords    TEXT,
  level       INTEGER,
  chapter     INTEGER,
  parent_code VARCHAR(20),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.7 Notas legales HS (mínimo viable)
CREATE TABLE IF NOT EXISTS hs_notes (
  id SERIAL PRIMARY KEY,
  scope TEXT NOT NULL,                -- 'section' | 'chapter' | 'heading' | 'subheading' ...
  scope_code TEXT NOT NULL,           -- p.ej: '87', '8706'
  note_number TEXT,                   -- p.ej: '1', '2a'
  text TEXT NOT NULL,                 -- contenido de la nota
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.8 Vínculos RGI ↔ HS (para rastreo/explicación)
CREATE TABLE IF NOT EXISTS rule_link_hs (
  id SERIAL PRIMARY KEY,
  rgi TEXT NOT NULL,                  -- p.ej: 'RGI1', 'RGI3b'
  hs6 TEXT NOT NULL,                  -- p.ej: '870690'
  priority INT DEFAULT 0,             -- desempate opcional
  note_id INT REFERENCES hs_notes(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices de apoyo
CREATE INDEX IF NOT EXISTS idx_hs_notes_scope ON hs_notes(scope, scope_code);
CREATE INDEX IF NOT EXISTS idx_rule_link_hs_hs6 ON rule_link_hs(hs6);

-- 1.9 rgi_rules (catálogo de reglas)
CREATE TABLE IF NOT EXISTS rgi_rules (
  id          BIGSERIAL PRIMARY KEY,
  rgi         VARCHAR(20) NOT NULL UNIQUE,
  description TEXT        NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.10 cases
CREATE TABLE IF NOT EXISTS cases (
  id            BIGSERIAL PRIMARY KEY,
  created_by    BIGINT      REFERENCES users(id) ON DELETE SET NULL,
  status        VARCHAR(30) NOT NULL DEFAULT 'open',
  product_title TEXT        NOT NULL,
  product_desc  TEXT,
  attrs_json    JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

-- 1.9 candidates
CREATE TABLE IF NOT EXISTS candidates (
  id               BIGSERIAL PRIMARY KEY,
  case_id          BIGINT      NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  hs6              VARCHAR(6),
  national_code    VARCHAR(10),
  confidence       NUMERIC(6,5),
  rationale        TEXT,
  legal_refs_json  JSONB,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_candidates_case ON candidates(case_id);

-- 2) Vistas
CREATE OR REPLACE VIEW v_current_tariff_items AS
SELECT
  id,
  national_code,
  COALESCE(hs6, LEFT(REGEXP_REPLACE(national_code, '\\D', '', 'g'), 6)) AS hs6,
  title,
  keywords,
  notes,
  COALESCE(active, TRUE) AS active,
  valid_from,
  valid_to,
  created_at,
  updated_at
FROM tariff_items
WHERE COALESCE(active, TRUE) = TRUE
  AND (valid_from IS NULL OR valid_from <= CURRENT_DATE)
  AND (valid_to   IS NULL OR valid_to   >= CURRENT_DATE);

-- 3) Seed

-- Usuarios con bcrypt (pgcrypto)
INSERT INTO users (email, password_hash, name, role, is_active)
VALUES
  ('juan.velez221@tau.usbmed.co', crypt('admin123', gen_salt('bf')), 'Juan Velez', 'admin', TRUE)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, password_hash, name, role, is_active)
VALUES
  ('adres.escobar221@tau.usbmed.edu.co', crypt('admin456', gen_salt('bf')), 'Adres Escobar', 'admin', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Reglas de mantenimiento
ANALYZE embeddings;
ANALYZE tariff_items;
ANALYZE cases;

-- 6) Normalización post-deploy (seguro si ya hay datos)
-- Asegura national_code de 10 dígitos sin puntos y hs6 consistente
UPDATE tariff_items
SET national_code = REGEXP_REPLACE(national_code, '\\D', '', 'g')
WHERE national_code ~ '[^0-9]';

UPDATE tariff_items
SET national_code = LPAD(national_code, 10, '0')
WHERE national_code ~ '^\\d+$' AND LENGTH(national_code) < 10;

UPDATE tariff_items
SET hs6 = LEFT(national_code, 6)
WHERE (hs6 IS NULL OR hs6 = '') AND national_code ~ '^\\d{10}$';

UPDATE tariff_items
SET active = TRUE
WHERE active IS NULL;

UPDATE tariff_items
SET valid_from = CURRENT_DATE
WHERE valid_from IS NULL;

-- 7) Índices finales (idempotentes)
CREATE UNIQUE INDEX IF NOT EXISTS uq_tariff_items_national ON tariff_items(national_code);

-- 4) Optional sample HS items (safe to keep for initial tests)
INSERT INTO hs_items (hs_code, title, keywords, level, chapter, parent_code)
VALUES
 ('8471.30.00', 'Computadoras portátiles, peso <= 10 kg', 'laptop, portátil, notebook', 6, 84, '8471.30')
ON CONFLICT (hs_code) DO NOTHING;

-- 5) Helper comment
-- After loading this schema:
--  - Ensure OPENAI_API_KEY / JWT_KEY are set in the API environment
--  - Import your tariff PDF with: python scripts/import_local_pdf.py "C:/ruta/arancel.pdf"
--  - Start API: python main.py
