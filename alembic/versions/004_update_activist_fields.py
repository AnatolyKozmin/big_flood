"""update activist fields

Revision ID: 004
Revises: 003
Create Date: 2024-12-07

Добавляет новые поля для активистов:
- group_name (Группа)
- phone (Номер телефона)
- has_license (Есть права)
- address (Адрес)

Также делает username обязательным полем.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новые поля
    op.add_column('activists', sa.Column('group_name', sa.String(255), nullable=True))
    op.add_column('activists', sa.Column('phone', sa.String(50), nullable=True))
    op.add_column('activists', sa.Column('has_license', sa.String(50), nullable=True))
    op.add_column('activists', sa.Column('address', sa.Text(), nullable=True))
    
    # Обновляем существующие записи где username NULL
    # Устанавливаем placeholder для записей без username
    op.execute("UPDATE activists SET username = 'unknown_' || id::text WHERE username IS NULL")
    
    # Делаем username NOT NULL
    op.alter_column('activists', 'username',
                    existing_type=sa.String(255),
                    nullable=False)


def downgrade() -> None:
    # Возвращаем username к nullable
    op.alter_column('activists', 'username',
                    existing_type=sa.String(255),
                    nullable=True)
    
    # Удаляем новые поля
    op.drop_column('activists', 'address')
    op.drop_column('activists', 'has_license')
    op.drop_column('activists', 'phone')
    op.drop_column('activists', 'group_name')

