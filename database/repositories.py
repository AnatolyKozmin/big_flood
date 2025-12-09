from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Chat, Quote, Activist, Reminder, MutedUser, MathDuel, ChatMember, QuoteTemplate


class ChatRepository:
    """Репозиторий для работы с чатами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, chat_id: int, title: Optional[str] = None) -> Chat:
        """Получить или создать чат по chat_id."""
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat is None:
            chat = Chat(chat_id=chat_id, title=title)
            self.session.add(chat)
            await self.session.commit()
            await self.session.refresh(chat)
        elif title and chat.title != title:
            chat.title = title
            await self.session.commit()
        
        return chat
    
    async def get_by_chat_id(self, chat_id: int) -> Optional[Chat]:
        """Получить чат по chat_id."""
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def set_chat_type(self, chat_id: int, chat_type: str) -> Optional[Chat]:
        """Установить тип чата (default, trainer)."""
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.chat_type = chat_type
            await self.session.commit()
            await self.session.refresh(chat)
        
        return chat
    
    async def get_all(self) -> Sequence[Chat]:
        """Получить все чаты."""
        stmt = select(Chat).order_by(Chat.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def set_google_sheet(self, chat_id: int, url: Optional[str]) -> Optional[Chat]:
        """Установить URL Google Sheets для чата."""
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.google_sheet_url = url
            if url:
                from datetime import datetime
                chat.google_sheet_synced_at = datetime.now()
            await self.session.commit()
            await self.session.refresh(chat)
        
        return chat
    
    async def set_quote_template(self, chat_id: int, path: Optional[str]) -> Optional[Chat]:
        """Установить путь к плашке для цитат."""
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.quote_template_path = path
            await self.session.commit()
            await self.session.refresh(chat)
        
        return chat


class QuoteRepository:
    """Репозиторий для работы с цитатами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(
        self,
        chat: Chat,
        text: str,
        added_by_id: int,
        added_by_name: Optional[str] = None,
        author_name: Optional[str] = None,
        author_id: Optional[int] = None,
    ) -> Quote:
        """Добавить новую цитату в чат."""
        quote = Quote(
            chat_pk=chat.id,
            text=text,
            author_name=author_name,
            author_id=author_id,
            added_by_id=added_by_id,
            added_by_name=added_by_name,
        )
        self.session.add(quote)
        await self.session.commit()
        await self.session.refresh(quote)
        return quote
    
    async def get_random_by_chat(self, chat: Chat) -> Optional[Quote]:
        """Получить случайную цитату из чата."""
        stmt = select(Quote).where(Quote.chat_pk == chat.id).order_by(func.random()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def count_by_chat(self, chat: Chat) -> int:
        """Получить количество цитат в чате."""
        stmt = select(func.count(Quote.id)).where(Quote.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()


class ActivistRepository:
    """Репозиторий для работы с активистами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(
        self,
        chat: Chat,
        full_name: str,
        username: str,
        surname: Optional[str] = None,
        group_name: Optional[str] = None,
        phone: Optional[str] = None,
        has_license: Optional[str] = None,
        address: Optional[str] = None,
        user_id: Optional[int] = None,
        info: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Activist:
        """Добавить активиста."""
        activist = Activist(
            chat_pk=chat.id,
            full_name=full_name,
            username=username,
            surname=surname,
            group_name=group_name,
            phone=phone,
            has_license=has_license,
            address=address,
            user_id=user_id,
            info=info,
            role=role,
        )
        self.session.add(activist)
        await self.session.commit()
        await self.session.refresh(activist)
        return activist
    
    async def find_by_query(self, chat: Chat, query: str) -> Optional[Activist]:
        """Найти активиста по фамилии или юзернейму."""
        query_lower = query.lower().strip().lstrip("@")
        stmt = select(Activist).where(
            Activist.chat_pk == chat.id,
            or_(
                func.lower(Activist.surname).contains(query_lower),
                func.lower(Activist.username) == query_lower,
                func.lower(Activist.full_name).contains(query_lower),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_by_user_id(self, chat: Chat, user_id: int) -> Optional[Activist]:
        """Найти активиста по Telegram user_id."""
        stmt = select(Activist).where(
            Activist.chat_pk == chat.id,
            Activist.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_random(self, chat: Chat) -> Optional[Activist]:
        """Получить случайного активиста."""
        stmt = select(Activist).where(Activist.chat_pk == chat.id).order_by(func.random()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, chat: Chat) -> Sequence[Activist]:
        """Получить всех активистов чата."""
        stmt = select(Activist).where(Activist.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def clear_all(self, chat: Chat) -> int:
        """Удалить всех активистов чата. Возвращает количество."""
        stmt = delete(Activist).where(Activist.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def count(self, chat: Chat) -> int:
        """Получить количество активистов в чате."""
        stmt = select(func.count(Activist.id)).where(Activist.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()


class ReminderRepository:
    """Репозиторий для работы с напоминаниями."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(
        self,
        chat: Chat,
        remind_at: datetime,
        created_by_id: int,
        created_by_name: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Reminder:
        """Создать напоминание."""
        reminder = Reminder(
            chat_pk=chat.id,
            text=text,
            remind_at=remind_at,
            created_by_id=created_by_id,
            created_by_name=created_by_name,
        )
        self.session.add(reminder)
        await self.session.commit()
        await self.session.refresh(reminder)
        return reminder
    
    async def get_pending(self, before: datetime) -> Sequence[Reminder]:
        """Получить все непосланные напоминания до указанного времени."""
        stmt = (
            select(Reminder)
            .where(Reminder.is_sent == False, Reminder.remind_at <= before)
            .order_by(Reminder.remind_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def mark_sent(self, reminder: Reminder) -> None:
        """Пометить напоминание как отправленное."""
        reminder.is_sent = True
        await self.session.commit()


class MutedUserRepository:
    """Репозиторий для работы с замученными пользователями."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(
        self,
        chat: Chat,
        user_id: int,
        muted_until: datetime,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> MutedUser:
        """Добавить замученного пользователя."""
        muted = MutedUser(
            chat_pk=chat.id,
            user_id=user_id,
            username=username,
            full_name=full_name,
            muted_until=muted_until,
            reason=reason,
        )
        self.session.add(muted)
        await self.session.commit()
        await self.session.refresh(muted)
        return muted
    
    async def get_active_mutes(self, chat: Chat) -> Sequence[MutedUser]:
        """Получить всех замученных в чате (с активным мутом)."""
        now = datetime.now()
        stmt = select(MutedUser).where(
            MutedUser.chat_pk == chat.id,
            MutedUser.muted_until > now
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def remove_all(self, chat: Chat) -> int:
        """Удалить все записи о мутах в чате. Возвращает количество."""
        stmt = delete(MutedUser).where(MutedUser.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount


class ChatMemberRepository:
    """Репозиторий для работы с участниками чата."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_or_update(
        self,
        chat: Chat,
        user_id: int,
        full_name: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> ChatMember:
        """Добавить или обновить участника чата."""
        stmt = select(ChatMember).where(
            ChatMember.chat_pk == chat.id,
            ChatMember.user_id == user_id
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        
        if member is None:
            member = ChatMember(
                chat_pk=chat.id,
                user_id=user_id,
                username=username,
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                message_count=1,
            )
            self.session.add(member)
        else:
            # Обновляем данные
            member.username = username
            member.full_name = full_name
            member.first_name = first_name
            member.last_name = last_name
            member.message_count += 1
        
        await self.session.commit()
        await self.session.refresh(member)
        return member
    
    async def get_all(self, chat: Chat) -> Sequence[ChatMember]:
        """Получить всех участников чата."""
        stmt = select(ChatMember).where(ChatMember.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_random(self, chat: Chat) -> Optional[ChatMember]:
        """Получить случайного участника чата."""
        stmt = select(ChatMember).where(ChatMember.chat_pk == chat.id).order_by(func.random()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, chat: Chat, user_id: int) -> Optional[ChatMember]:
        """Получить участника по user_id."""
        stmt = select(ChatMember).where(
            ChatMember.chat_pk == chat.id,
            ChatMember.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_by_query(self, chat: Chat, query: str) -> Optional[ChatMember]:
        """Найти участника по имени или юзернейму."""
        query_lower = query.lower().strip().lstrip("@")
        stmt = select(ChatMember).where(
            ChatMember.chat_pk == chat.id,
            or_(
                func.lower(ChatMember.username) == query_lower,
                func.lower(ChatMember.full_name).contains(query_lower),
                func.lower(ChatMember.last_name).contains(query_lower),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class MathDuelRepository:
    """Репозиторий для работы с математическими дуэлями."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        chat: Chat,
        challenger_id: int,
        challenger_name: str,
        opponent_id: int,
        opponent_name: str,
        expression: str,
        answer: int,
        expires_at: datetime,
    ) -> MathDuel:
        """Создать дуэль."""
        duel = MathDuel(
            chat_pk=chat.id,
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            expression=expression,
            answer=answer,
            expires_at=expires_at,
        )
        self.session.add(duel)
        await self.session.commit()
        await self.session.refresh(duel)
        return duel
    
    async def get_active_for_user(self, chat: Chat, user_id: int) -> Optional[MathDuel]:
        """Получить активную дуэль, где участвует пользователь."""
        now = datetime.now()
        stmt = select(MathDuel).where(
            MathDuel.chat_pk == chat.id,
            MathDuel.is_active == True,
            MathDuel.expires_at > now,
            or_(
                MathDuel.challenger_id == user_id,
                MathDuel.opponent_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_in_chat(self, chat: Chat) -> Sequence[MathDuel]:
        """Получить все активные дуэли в чате."""
        now = datetime.now()
        stmt = select(MathDuel).where(
            MathDuel.chat_pk == chat.id,
            MathDuel.is_active == True,
            MathDuel.expires_at > now,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def finish_duel(self, duel: MathDuel, winner_id: Optional[int] = None) -> None:
        """Завершить дуэль."""
        duel.is_active = False
        duel.winner_id = winner_id
        await self.session.commit()
    
    async def expire_old_duels(self) -> int:
        """Завершить все истекшие дуэли."""
        now = datetime.now()
        stmt = select(MathDuel).where(
            MathDuel.is_active == True,
            MathDuel.expires_at <= now,
        )
        result = await self.session.execute(stmt)
        duels = result.scalars().all()
        
        for duel in duels:
            duel.is_active = False
        
        await self.session.commit()
        return len(duels)


class QuoteTemplateRepository:
    """Репозиторий для работы с шаблонами цитат."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, chat: Chat) -> QuoteTemplate:
        """Получить или создать шаблон для чата."""
        stmt = select(QuoteTemplate).where(QuoteTemplate.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        template = result.scalar_one_or_none()
        
        if template is None:
            template = QuoteTemplate(chat_pk=chat.id)
            self.session.add(template)
            await self.session.commit()
            await self.session.refresh(template)
        
        return template
    
    async def get_by_chat(self, chat: Chat) -> Optional[QuoteTemplate]:
        """Получить шаблон для чата."""
        stmt = select(QuoteTemplate).where(QuoteTemplate.chat_pk == chat.id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        template: QuoteTemplate,
        **kwargs
    ) -> QuoteTemplate:
        """Обновить настройки шаблона."""
        for key, value in kwargs.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
        
        await self.session.commit()
        await self.session.refresh(template)
        return template
    
    async def delete(self, template: QuoteTemplate) -> None:
        """Удалить шаблон."""
        await self.session.delete(template)
        await self.session.commit()
