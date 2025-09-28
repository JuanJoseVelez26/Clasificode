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

-- 1.3 tariff_items
CREATE TABLE IF NOT EXISTS tariff_items (
  id             BIGSERIAL PRIMARY KEY,
  hs_code6       VARCHAR(6)  NOT NULL,
  national_code  VARCHAR(10) NOT NULL,
  title          TEXT        NOT NULL,
  legal_basis_id BIGINT      REFERENCES legal_sources(id) ON DELETE SET NULL,
  valid_from     TIMESTAMPTZ,
  valid_to       TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (national_code)
);
CREATE INDEX IF NOT EXISTS idx_tariff_items_hs6 ON tariff_items(hs_code6);
CREATE INDEX IF NOT EXISTS idx_tariff_items_valid ON tariff_items(valid_from, valid_to);

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

-- 1.7 rgi_rules
CREATE TABLE IF NOT EXISTS rgi_rules (
  id          BIGSERIAL PRIMARY KEY,
  rgi         VARCHAR(20) NOT NULL UNIQUE,
  description TEXT        NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.8 cases
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
SELECT *
FROM tariff_items
WHERE valid_from <= NOW()
  AND (valid_to IS NULL OR valid_to > NOW());

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
