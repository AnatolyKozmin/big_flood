import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from config import REDIS_URL

logger = logging.getLogger(__name__)


class RedisCache:
    """Асинхронный Redis клиент."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Подключение к Redis."""
        if self._client is None:
            self._client = redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis")
    
    async def disconnect(self):
        """Отключение от Redis."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")
    
    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        """Получить значение по ключу."""
        return await self.client.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """Установить значение с опциональным TTL в секундах."""
        return await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> int:
        """Удалить ключ."""
        return await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Проверить существование ключа."""
        return await self.client.exists(key) > 0
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Установить поле в хэше."""
        return await self.client.hset(name, key, value)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Получить поле из хэша."""
        return await self.client.hget(name, key)
    
    async def hgetall(self, name: str) -> dict:
        """Получить все поля хэша."""
        return await self.client.hgetall(name)
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Удалить поля из хэша."""
        return await self.client.hdel(name, *keys)
    
    async def sadd(self, name: str, *values: str) -> int:
        """Добавить значения в множество."""
        return await self.client.sadd(name, *values)
    
    async def smembers(self, name: str) -> set:
        """Получить все элементы множества."""
        return await self.client.smembers(name)
    
    async def srandmember(self, name: str, count: int = 1) -> list:
        """Получить случайные элементы из множества."""
        return await self.client.srandmember(name, count)
    
    async def scard(self, name: str) -> int:
        """Получить количество элементов в множестве."""
        return await self.client.scard(name)
    
    async def expire(self, name: str, seconds: int) -> bool:
        """Установить TTL для ключа."""
        return await self.client.expire(name, seconds)
    
    async def set_json(self, key: str, data: Any, expire: Optional[int] = None) -> bool:
        """Сохранить JSON данные."""
        return await self.set(key, json.dumps(data, ensure_ascii=False), expire)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Получить JSON данные."""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None


# Глобальный инстанс
redis_client = RedisCache()

