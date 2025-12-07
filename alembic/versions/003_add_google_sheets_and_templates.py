"""add google sheets and templates

Revision ID: 003
Revises: 002_add_chat_type
Create Date: 2024-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002_add_chat_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поля для Google Sheets
    op.add_column('chats', sa.Column('google_sheet_url', sa.String(500), nullable=True))
    op.add_column('chats', sa.Column('google_sheet_synced_at', sa.DateTime(timezone=True), nullable=True))
    
    # Добавляем поле для плашки цитат
    op.add_column('chats', sa.Column('quote_template_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('chats', 'quote_template_path')
    op.drop_column('chats', 'google_sheet_synced_at')
    op.drop_column('chats', 'google_sheet_url')

