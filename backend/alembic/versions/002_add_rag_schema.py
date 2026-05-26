"""add_rag_schema

Revision ID: 002
Revises: 001_initial
Create Date: 2026-05-26 17:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Knowledge Base Articles
    op.create_table(
        'knowledge_base_articles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('embedding', Vector(dim=1536), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_category', 'knowledge_base_articles', ['category'], unique=False)
    op.create_index('ix_kb_is_published', 'knowledge_base_articles', ['is_published'], unique=False)
    op.create_index('ix_kb_search_vector', 'knowledge_base_articles', ['search_vector'], unique=False, postgresql_using='gin')

    # Tickets search_vector
    op.add_column('tickets', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True))
    op.create_index('ix_tickets_search_vector', 'tickets', ['search_vector'], unique=False, postgresql_using='gin')

    # Ticket Comments embedding & search_vector
    op.add_column('ticket_comments', sa.Column('embedding', Vector(dim=1536), nullable=True))
    op.add_column('ticket_comments', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True))
    op.create_index('ix_ticket_comments_search_vector', 'ticket_comments', ['search_vector'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_ticket_comments_search_vector', table_name='ticket_comments', postgresql_using='gin')
    op.drop_column('ticket_comments', 'search_vector')
    op.drop_column('ticket_comments', 'embedding')

    op.drop_index('ix_tickets_search_vector', table_name='tickets', postgresql_using='gin')
    op.drop_column('tickets', 'search_vector')

    op.drop_index('ix_kb_search_vector', table_name='knowledge_base_articles', postgresql_using='gin')
    op.drop_index('ix_kb_is_published', table_name='knowledge_base_articles')
    op.drop_index('ix_kb_category', table_name='knowledge_base_articles')
    op.drop_table('knowledge_base_articles')
