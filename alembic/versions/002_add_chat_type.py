"""Add chat_type column

Revision ID: 002_add_chat_type
Revises: 001_initial
Create Date: 2024-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_add_chat_type'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chats', sa.Column('chat_type', sa.String(length=50), nullable=False, server_default='default'))


def downgrade() -> None:
    op.drop_column('chats', 'chat_type')

