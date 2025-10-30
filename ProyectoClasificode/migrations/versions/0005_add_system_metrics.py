"""Add system_metrics table

Revision ID: 0005_add_system_metrics
Revises: 0004_fix_embeddings_table
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005_add_system_metrics'
down_revision = '0004_fix_embeddings_table'
branch_labels = None
depends_on = None


def upgrade():
    """Crear tabla system_metrics para métricas técnicas del sistema"""
    
    # Crear tabla system_metrics
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Crear índices para optimizar consultas
    op.create_index('ix_system_metrics_metric_name', 'system_metrics', ['metric_name'])
    op.create_index('ix_system_metrics_created_at', 'system_metrics', ['created_at'])
    op.create_index('ix_system_metrics_name_created', 'system_metrics', ['metric_name', 'created_at'])


def downgrade():
    """Eliminar tabla system_metrics"""
    
    # Eliminar índices
    op.drop_index('ix_system_metrics_name_created', table_name='system_metrics')
    op.drop_index('ix_system_metrics_created_at', table_name='system_metrics')
    op.drop_index('ix_system_metrics_metric_name', table_name='system_metrics')
    
    # Eliminar tabla
    op.drop_table('system_metrics')
