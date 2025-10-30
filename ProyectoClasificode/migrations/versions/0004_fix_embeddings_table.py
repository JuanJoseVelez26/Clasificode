"""Fix embeddings table structure

Revision ID: 0004
Revises: 0003
Create Date: 2025-10-11 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004_fix_embeddings_table'
down_revision = '0003_add_embeddings_table'
branch_labels = None
depends_on = None

def upgrade():
    # Asegurar que la extensión pgvector esté habilitada
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Crear la tabla embeddings si no existe
    op.execute("""
    DO $$
    BEGIN
        -- Eliminar la tabla si existe (solo para desarrollo)
        DROP TABLE IF EXISTS public.embeddings CASCADE;
        
        -- Crear la tabla con la estructura correcta
        CREATE TABLE IF NOT EXISTS public.embeddings (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            owner_type VARCHAR(50) NOT NULL,
            owner_id INTEGER NOT NULL,
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(100) NOT NULL,
            dim INTEGER NOT NULL,
            vector VECTOR(1536) NOT NULL,
            text_norm TEXT NOT NULL,
            meta JSONB,
            
            -- Restricción única
            CONSTRAINT uq_embedding_owner UNIQUE (owner_type, owner_id, provider, model)
        );
        
        -- Índice para búsquedas por propietario
        CREATE INDEX IF NOT EXISTS idx_embeddings_owner ON public.embeddings(owner_type, owner_id);
        
        -- Índice para búsquedas vectoriales (solo si hay suficientes datos)
        -- CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON public.embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
        
        -- Comentarios para documentación
        COMMENT ON TABLE public.embeddings IS 'Almacena los embeddings vectoriales para búsqueda semántica';
        COMMENT ON COLUMN public.embeddings.owner_type IS 'Tipo de entidad propietaria del embedding (ej: hs_item, case)';
        COMMENT ON COLUMN public.embeddings.owner_id IS 'ID de la entidad propietaria';
        COMMENT ON COLUMN public.embeddings.provider IS 'Proveedor del embedding (ej: openai, huggingface)';
        COMMENT ON COLUMN public.embeddings.model IS 'Modelo usado para generar el embedding';
        COMMENT ON COLUMN public.embeddings.dim IS 'Dimensión del vector de embedding';
        COMMENT ON COLUMN public.embeddings.vector IS 'Vector de embedding';
        COMMENT ON COLUMN public.embeddings.text_norm IS 'Texto normalizado usado para generar el embedding';
        COMMENT ON COLUMN public.embeddings.meta IS 'Metadatos adicionales en formato JSON';
    END
    $$;
    """)

def downgrade():
    # Eliminar la tabla embeddings
    op.execute("DROP TABLE IF EXISTS public.embeddings CASCADE;")
    # Opcional: eliminar la extensión (solo si no la usan otras tablas)
    # op.execute('DROP EXTENSION IF EXISTS vector;')
