import json
import logging
import random
from dataclasses import dataclass, asdict
from typing import Optional

from .redis_client import redis_client

logger = logging.getLogger(__name__)

# TTL для кэша участников чата - 24 часа
MEMBERS_CACHE_TTL = 60 * 60 * 24


@dataclass
class CachedMember:
    """Структура закэшированного участника чата."""
    user_id: int
    username: Optional[str]
    full_name: str
    first_name: Optional[str]
    last_name: Optional[str]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, data: str) -> "CachedMember":
        return cls(**json.loads(data))


class ChatMembersCache:
    """Кэш участников чата в Redis."""
    
    @staticmethod
    def _key(chat_id: int) -> str:
        """Ключ для хэша участников конкретного чата."""
        return f"chat:{chat_id}:members"
    
    @classmethod
    async def add_member(
        cls,
        chat_id: int,
        user_id: int,
        username: Optional[str],
        full_name: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> None:
        """Добавить/обновить участника в кэше."""
        member = CachedMember(
            user_id=user_id,
            username=username,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
        )
        
        key = cls._key(chat_id)
        await redis_client.hset(key, str(user_id), member.to_json())
        await redis_client.expire(key, MEMBERS_CACHE_TTL)
    
    @classmethod
    async def get_member(cls, chat_id: int, user_id: int) -> Optional[CachedMember]:
        """Получить участника из кэша."""
        key = cls._key(chat_id)
        data = await redis_client.hget(key, str(user_id))
        if data:
            return CachedMember.from_json(data)
        return None
    
    @classmethod
    async def get_all_members(cls, chat_id: int) -> list[CachedMember]:
        """Получить всех участников чата из кэша."""
        key = cls._key(chat_id)
        data = await redis_client.hgetall(key)
        
        members = []
        for member_data in data.values():
            try:
                members.append(CachedMember.from_json(member_data))
            except Exception as e:
                logger.warning(f"Failed to parse member data: {e}")
        
        return members
    
    @classmethod
    async def get_random_member(cls, chat_id: int) -> Optional[CachedMember]:
        """Получить случайного участника чата."""
        members = await cls.get_all_members(chat_id)
        if members:
            return random.choice(members)
        return None
    
    @classmethod
    async def get_member_count(cls, chat_id: int) -> int:
        """Получить количество участников в кэше."""
        key = cls._key(chat_id)
        data = await redis_client.hgetall(key)
        return len(data)
    
    @classmethod
    async def remove_member(cls, chat_id: int, user_id: int) -> None:
        """Удалить участника из кэша."""
        key = cls._key(chat_id)
        await redis_client.hdel(key, str(user_id))

