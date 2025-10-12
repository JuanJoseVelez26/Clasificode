"""Add embeddings table for vector search

Revision ID: 0003
Revises: 0002
Create Date: 2025-10-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # Asegurar que la extensión pgvector esté instalada
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Crear la tabla embeddings si no existe
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'embeddings') THEN
            CREATE TABLE public.embeddings (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                owner_type VARCHAR(20) NOT NULL,
                owner_id INTEGER NOT NULL,
                provider VARCHAR(50) NOT NULL,
                model VARCHAR(50) NOT NULL,
                dim INTEGER NOT NULL,
                vector VECTOR(1536) NOT NULL,
                text_norm TEXT NOT NULL,
                meta JSONB,
                CONSTRAINT uq_embedding_owner UNIQUE (owner_type, owner_id, provider, model)
            );
            
            -- Índice para búsquedas por owner
            CREATE INDEX idx_embeddings_owner ON public.embeddings(owner_type, owner_id);
            
            -- Índice para búsquedas vectoriales (solo si hay suficientes datos)
            -- CREATE INDEX idx_embeddings_vector ON public.embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
        END IF;
    END
    $$;
    """)

def downgrade():
    # Eliminar la tabla embeddings si existe
    op.execute("""
    DROP TABLE IF EXISTS public.embeddings CASCADE;
    """)
