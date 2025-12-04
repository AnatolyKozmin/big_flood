from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class Chat(Base):
    """Модель чата (группы)."""
    
    __tablename__ = "chats"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(50), default="default", nullable=False)  # default, trainer
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Связи
    quotes: Mapped[list["Quote"]] = relationship(
        "Quote", back_populates="chat", cascade="all, delete-orphan"
    )
    activists: Mapped[list["Activist"]] = relationship(
        "Activist", back_populates="chat", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder", back_populates="chat", cascade="all, delete-orphan"
    )
    muted_users: Mapped[list["MutedUser"]] = relationship(
        "MutedUser", back_populates="chat", cascade="all, delete-orphan"
    )
    math_duels: Mapped[list["MathDuel"]] = relationship(
        "MathDuel", back_populates="chat", cascade="all, delete-orphan"
    )
    members: Mapped[list["ChatMember"]] = relationship(
        "ChatMember", back_populates="chat", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Chat(id={self.id}, chat_id={self.chat_id}, title={self.title})>"


class ChatMember(Base):
    """Модель участника чата (все кто писал в чат)."""
    
    __tablename__ = "chat_members"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_pk: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    message_count: Mapped[int] = mapped_column(Integer, default=1)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="members")
    
    # Уникальность пользователя в рамках чата
    __table_args__ = (
        sa.UniqueConstraint('chat_pk', 'user_id', name='uq_chat_member'),
    )
    
    def __repr__(self) -> str:
        return f"<ChatMember(id={self.id}, user_id={self.user_id}, full_name={self.full_name})>"


class Activist(Base):
    """Модель активиста с информацией."""
    
    __tablename__ = "activists"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_pk: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    surname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Информация об активисте
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="activists")
    
    def __repr__(self) -> str:
        return f"<Activist(id={self.id}, full_name={self.full_name})>"


class Quote(Base):
    """Модель цитаты."""
    
    __tablename__ = "quotes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_pk: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    added_by_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    added_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="quotes")
    
    def __repr__(self) -> str:
        return f"<Quote(id={self.id}, text={self.text[:30]}...)>"


class Reminder(Base):
    """Модель напоминания (!разбудить)."""
    
    __tablename__ = "reminders"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_pk: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="reminders")
    
    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, remind_at={self.remind_at})>"


class MutedUser(Base):
    """Модель замученного пользователя (для !анмут)."""
    
    __tablename__ = "muted_users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_pk: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    muted_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="muted_users")
    
    def __repr__(self) -> str:
        return f"<MutedUser(id={self.id}, user_id={self.user_id})>"


class MathDuel(Base):
    """Модель математической дуэли."""
    
    __tablename__ = "math_duels"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_pk: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    challenger_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    challenger_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    opponent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    opponent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Задача
    expression: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    winner_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="math_duels")
    
    def __repr__(self) -> str:
        return f"<MathDuel(id={self.id}, challenger={self.challenger_id} vs {self.opponent_id})>"
