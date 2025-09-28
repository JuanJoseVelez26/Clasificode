"""DBA updates: constraints, view, scraping columns, audit table, and params tweak

Revision ID: 0002
Revises: 0001
Create Date: 2025-09-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Asegurar constraint para 10 dígitos en tariff_items.national_code
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.tariff_items') IS NOT NULL THEN
                -- Crear constraint si no existe
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    WHERE t.relname = 'tariff_items' AND c.conname = 'ck_tariff_items_national_code_10_digits'
                ) THEN
                    -- Verificar que la columna exista antes de crear el constraint
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'tariff_items' AND column_name = 'national_code'
                    ) THEN
                        EXECUTE 'ALTER TABLE public.tariff_items
                                 ADD CONSTRAINT ck_tariff_items_national_code_10_digits
                                 CHECK (national_code ~ ''^[0-9]{10}$'')';
                    END IF;
                END IF;
            END IF;
        END
        $$;
        """
    )

    # 2) Crear/actualizar vista de códigos vigentes
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.tariff_items') IS NOT NULL THEN
                -- Crear o reemplazar la vista solo si la tabla base existe
                EXECUTE 'CREATE OR REPLACE VIEW public.v_current_tariff_items AS
                         SELECT *
                         FROM public.tariff_items
                         WHERE (valid_from IS NULL OR valid_from <= now())
                           AND (valid_to   IS NULL OR valid_to   >= now())';
            END IF;
        END
        $$;
        """
    )

    # 3) Agregar columnas de scraping a legal_sources
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.legal_sources') IS NOT NULL THEN
                -- fetched_by TEXT
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'legal_sources' AND column_name = 'fetched_by'
                ) THEN
                    EXECUTE 'ALTER TABLE public.legal_sources ADD COLUMN fetched_by TEXT';
                END IF;

                -- raw_html BYTEA
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'legal_sources' AND column_name = 'raw_html'
                ) THEN
                    EXECUTE 'ALTER TABLE public.legal_sources ADD COLUMN raw_html BYTEA';
                END IF;
            END IF;
        END
        $$;
        """
    )

    # 4) Crear tabla de auditoría de scraping: source_sync_runs
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.source_sync_runs') IS NULL THEN
                EXECUTE 'CREATE TABLE public.source_sync_runs (
                            id BIGSERIAL PRIMARY KEY,
                            source_name TEXT NOT NULL,
                            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                            finished_at TIMESTAMPTZ NULL,
                            status TEXT NOT NULL,
                            items_upserted INTEGER NOT NULL DEFAULT 0,
                            error TEXT NULL
                        )';
                -- Índices útiles
                EXECUTE 'CREATE INDEX IF NOT EXISTS idx_source_sync_runs_source ON public.source_sync_runs (source_name)';
                EXECUTE 'CREATE INDEX IF NOT EXISTS idx_source_sync_runs_started ON public.source_sync_runs (started_at)';
                EXECUTE 'CREATE INDEX IF NOT EXISTS idx_source_sync_runs_status ON public.source_sync_runs (status)';
            END IF;
        END
        $$;
        """
    )

    # 5) Configurar system_params: k_top = 1 (idempotente, tolerante a diferentes esquemas)
    op.execute(
        """
        DO $$
        DECLARE
            key_col text := NULL;
            val_col text := NULL;
            stmt text;
        BEGIN
            IF to_regclass('public.system_params') IS NOT NULL THEN
                -- Detectar posibles nombres de columnas clave/valor
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='key') THEN
                    key_col := 'key';
                ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='name') THEN
                    key_col := 'name';
                ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='param_key') THEN
                    key_col := 'param_key';
                ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='param') THEN
                    key_col := 'param';
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='value') THEN
                    val_col := 'value';
                ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='param_value') THEN
                    val_col := 'param_value';
                ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_params' AND column_name='val') THEN
                    val_col := 'val';
                END IF;

                IF key_col IS NOT NULL AND val_col IS NOT NULL THEN
                    -- Intentar UPDATE, si no afectó filas, hacer INSERT
                    stmt := format('UPDATE public.system_params SET %I = %L WHERE %I = %L', val_col, '1', key_col, 'k_top');
                    EXECUTE stmt;
                    IF NOT FOUND THEN
                        stmt := format('INSERT INTO public.system_params(%I, %I) VALUES(%L, %L)', key_col, val_col, 'k_top', '1');
                        EXECUTE stmt;
                    END IF;
                END IF;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Revertir 5) k_top cambio no es estrictamente necesario revertir valor; no se hace rollback de parámetros.
    # Opcionalmente podríamos intentar restaurar un valor previo si existiera, pero no hay historial.

    # 4) Eliminar tabla source_sync_runs si existe
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.source_sync_runs') IS NOT NULL THEN
                EXECUTE 'DROP TABLE IF EXISTS public.source_sync_runs';
            END IF;
        END
        $$;
        """
    )

    # 3) Quitar columnas en legal_sources si existen
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.legal_sources') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'legal_sources' AND column_name = 'fetched_by'
                ) THEN
                    EXECUTE 'ALTER TABLE public.legal_sources DROP COLUMN fetched_by';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'legal_sources' AND column_name = 'raw_html'
                ) THEN
                    EXECUTE 'ALTER TABLE public.legal_sources DROP COLUMN raw_html';
                END IF;
            END IF;
        END
        $$;
        """
    )

    # 2) Eliminar vista v_current_tariff_items si existe
    op.execute("DROP VIEW IF EXISTS public.v_current_tariff_items;")

    # 1) Quitar constraint en tariff_items si existe
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.tariff_items') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    WHERE t.relname = 'tariff_items' AND c.conname = 'ck_tariff_items_national_code_10_digits'
                ) THEN
                    EXECUTE 'ALTER TABLE public.tariff_items DROP CONSTRAINT ck_tariff_items_national_code_10_digits';
                END IF;
            END IF;
        END
        $$;
        """
    )
