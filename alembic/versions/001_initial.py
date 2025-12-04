"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Chats table
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('chat_type', sa.String(length=50), nullable=False, server_default='default'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )
    op.create_index('ix_chats_chat_id', 'chats', ['chat_id'], unique=True)

    # Activists table
    op.create_table(
        'activists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('surname', sa.String(length=255), nullable=True),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('role', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_activists_user_id', 'activists', ['user_id'])
    op.create_index('ix_activists_username', 'activists', ['username'])
    op.create_index('ix_activists_surname', 'activists', ['surname'])

    # Quotes table
    op.create_table(
        'quotes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('author_id', sa.BigInteger(), nullable=True),
        sa.Column('added_by_id', sa.BigInteger(), nullable=False),
        sa.Column('added_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Reminders table
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('remind_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.BigInteger(), nullable=False),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('is_sent', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reminders_remind_at', 'reminders', ['remind_at'])

    # Muted users table
    op.create_table(
        'muted_users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('muted_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_muted_users_user_id', 'muted_users', ['user_id'])

    # Math duels table
    op.create_table(
        'math_duels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        sa.Column('challenger_id', sa.BigInteger(), nullable=False),
        sa.Column('challenger_name', sa.String(length=255), nullable=True),
        sa.Column('opponent_id', sa.BigInteger(), nullable=False),
        sa.Column('opponent_name', sa.String(length=255), nullable=True),
        sa.Column('expression', sa.String(length=255), nullable=False),
        sa.Column('answer', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('winner_id', sa.BigInteger(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Chat members table (all users who wrote in chat)
    op.create_table(
        'chat_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_pk', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('message_count', sa.Integer(), default=1, nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_pk'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_pk', 'user_id', name='uq_chat_member')
    )
    op.create_index('ix_chat_members_user_id', 'chat_members', ['user_id'])


def downgrade() -> None:
    op.drop_table('chat_members')
    op.drop_table('math_duels')
    op.drop_table('muted_users')
    op.drop_table('reminders')
    op.drop_table('quotes')
    op.drop_table('activists')
    op.drop_table('chats')

