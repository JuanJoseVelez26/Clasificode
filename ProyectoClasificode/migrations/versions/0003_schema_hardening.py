"""Schema hardening: uniques, FKs, and indexes

Revision ID: 0003
Revises: 0002
Create Date: 2025-09-13 00:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) legal_sources.content_hash UNIQUE (o al menos index)
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.legal_sources') IS NOT NULL THEN
                -- Crear índice único si no existe
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'uq_legal_sources_content_hash' AND n.nspname = 'public'
                ) THEN
                    CREATE UNIQUE INDEX uq_legal_sources_content_hash ON public.legal_sources (content_hash);
                END IF;
                -- Índice por fetched_at
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_legal_sources_fetched_at' AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX idx_legal_sources_fetched_at ON public.legal_sources (fetched_at);
                END IF;
            END IF;
        END
        $$;
        """
    )

    # 2) tariff_items.national_code UNIQUE + índices
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.tariff_items') IS NOT NULL THEN
                -- Índice único por national_code
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'uq_tariff_items_national_code' AND n.nspname = 'public'
                ) THEN
                    CREATE UNIQUE INDEX uq_tariff_items_national_code ON public.tariff_items (national_code);
                END IF;
                -- Índices operativos
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_tariff_items_legal_basis_id' AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX idx_tariff_items_legal_basis_id ON public.tariff_items (legal_basis_id);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_tariff_items_valid_from' AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX idx_tariff_items_valid_from ON public.tariff_items (valid_from);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_tariff_items_valid_to' AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX idx_tariff_items_valid_to ON public.tariff_items (valid_to);
                END IF;
                -- CHECK coherencia de vigencias
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'ck_tariff_items_valid_range'
                ) THEN
                    ALTER TABLE public.tariff_items
                    ADD CONSTRAINT ck_tariff_items_valid_range
                    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from);
                END IF;
            END IF;
        END
        $$;
        """
    )

    # 3) FK tariff_items.legal_basis_id -> legal_sources(id)
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.tariff_items') IS NOT NULL AND to_regclass('public.legal_sources') IS NOT NULL THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_tariff_items_legal_basis'
                ) THEN
                    ALTER TABLE public.tariff_items
                    ADD CONSTRAINT fk_tariff_items_legal_basis
                    FOREIGN KEY (legal_basis_id) REFERENCES public.legal_sources(id)
                    ON UPDATE CASCADE ON DELETE SET NULL;
                END IF;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Revertir FK
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.tariff_items') IS NOT NULL THEN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_tariff_items_legal_basis') THEN
                    ALTER TABLE public.tariff_items DROP CONSTRAINT fk_tariff_items_legal_basis;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_tariff_items_valid_range') THEN
                    ALTER TABLE public.tariff_items DROP CONSTRAINT ck_tariff_items_valid_range;
                END IF;
                DROP INDEX IF EXISTS idx_tariff_items_valid_to;
                DROP INDEX IF EXISTS idx_tariff_items_valid_from;
                DROP INDEX IF EXISTS idx_tariff_items_legal_basis_id;
                DROP INDEX IF EXISTS uq_tariff_items_national_code;
            END IF;
            IF to_regclass('public.legal_sources') IS NOT NULL THEN
                DROP INDEX IF EXISTS idx_legal_sources_fetched_at;
                DROP INDEX IF EXISTS uq_legal_sources_content_hash;
            END IF;
        END
        $$;
        """
    )
