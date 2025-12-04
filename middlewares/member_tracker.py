import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from cache.chat_members import ChatMembersCache
from database.engine import async_session
from database.repositories import ChatRepository, ChatMemberRepository

logger = logging.getLogger(__name__)


class MemberTrackerMiddleware(BaseMiddleware):
    """
    Middleware для автоматического отслеживания участников чата.
    Сохраняет каждого кто пишет в Redis кэш и периодически в БД.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Обрабатываем только сообщения в группах
        if event.chat.type not in ("group", "supergroup"):
            return await handler(event, data)
        
        # Пропускаем ботов
        if event.from_user is None or event.from_user.is_bot:
            return await handler(event, data)
        
        user = event.from_user
        chat_id = event.chat.id
        
        try:
            # Сохраняем в Redis кэш (быстро)
            await ChatMembersCache.add_member(
                chat_id=chat_id,
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            
            # Асинхронно сохраняем в БД (в фоне, без блокировки)
            # Используем отдельную сессию чтобы не блокировать основной хендлер
            async with async_session() as session:
                chat_repo = ChatRepository(session)
                member_repo = ChatMemberRepository(session)
                
                chat = await chat_repo.get_or_create(chat_id, event.chat.title)
                await member_repo.add_or_update(
                    chat=chat,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
        except Exception as e:
            # Не ломаем бота если трекинг упал
            logger.warning(f"Failed to track member: {e}")
        
        return await handler(event, data)

