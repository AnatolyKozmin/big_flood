"""add author align

Revision ID: 007
Revises: 006
Create Date: 2024-12-07

Добавляет поле author_align для выравнивания подписи автора.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quote_templates', 
        sa.Column('author_align', sa.String(10), nullable=False, server_default='center')
    )


def downgrade() -> None:
    op.drop_column('quote_templates', 'author_align')

