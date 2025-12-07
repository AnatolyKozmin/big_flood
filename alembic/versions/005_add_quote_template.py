"""add quote template

Revision ID: 005
Revises: 004
Create Date: 2024-12-07

Добавляет таблицу quote_templates для хранения настроек шаблонов цитат.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'quote_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        
        # Размеры картинки
        sa.Column('image_width', sa.Integer(), nullable=False, server_default='800'),
        sa.Column('image_height', sa.Integer(), nullable=False, server_default='600'),
        
        # Фон
        sa.Column('background_path', sa.String(500), nullable=True),
        sa.Column('background_color', sa.String(20), nullable=False, server_default='#1e1e28'),
        
        # Область текста
        sa.Column('text_x', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('text_y', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('text_width', sa.Integer(), nullable=False, server_default='680'),
        sa.Column('text_height', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('text_color', sa.String(20), nullable=False, server_default='#ffffff'),
        sa.Column('text_font_size', sa.Integer(), nullable=False, server_default='32'),
        
        # Аватарка
        sa.Column('avatar_x', sa.Integer(), nullable=False, server_default='350'),
        sa.Column('avatar_y', sa.Integer(), nullable=False, server_default='420'),
        sa.Column('avatar_size', sa.Integer(), nullable=False, server_default='80'),
        sa.Column('avatar_enabled', sa.Boolean(), nullable=False, server_default='true'),
        
        # Автор
        sa.Column('author_x', sa.Integer(), nullable=False, server_default='400'),
        sa.Column('author_y', sa.Integer(), nullable=False, server_default='520'),
        sa.Column('author_color', sa.String(20), nullable=False, server_default='#ffc107'),
        sa.Column('author_font_size', sa.Integer(), nullable=False, server_default='24'),
        
        # Шрифт
        sa.Column('font_path', sa.String(500), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('chat_pk', name='uq_quote_template_chat')
    )


def downgrade() -> None:
    op.drop_table('quote_templates')

