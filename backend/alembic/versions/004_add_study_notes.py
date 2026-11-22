"""add study_notes table

Revision ID: 004_study_notes
Revises: 003_user_streaks
Create Date: 2026-11-22 20:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004_study_notes'
down_revision: Union[str, None] = '003_user_streaks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'study_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False, server_default='General Studies'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_study_notes_user_id', 'study_notes', ['user_id'])
    op.create_index('ix_study_notes_created_at', 'study_notes', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_study_notes_created_at', table_name='study_notes')
    op.drop_index('ix_study_notes_user_id', table_name='study_notes')
    op.drop_table('study_notes')
