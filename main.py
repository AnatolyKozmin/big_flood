import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import main_router
from middlewares import DatabaseMiddleware, MemberTrackerMiddleware
from scheduler import scheduler_loop
from cache import redis_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("Connecting to Redis...")
    await redis_client.connect()
    logger.info("Redis connected!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    logger.info("Disconnecting from Redis...")
    await redis_client.disconnect()
    logger.info("Redis disconnected!")


async def main():
    """Главная функция запуска бота."""
    logger.info("Starting bot...")
    
    # Создаём бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем startup/shutdown хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Регистрируем middleware
    # Порядок важен: сначала трекинг участников, потом БД
    dp.message.middleware(MemberTrackerMiddleware())
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.my_chat_member.middleware(DatabaseMiddleware())
    
    # Регистрируем роутеры
    dp.include_router(main_router)
    
    # Удаляем вебхук и запускаем планировщик
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем планировщик напоминаний в фоне
    asyncio.create_task(scheduler_loop(bot))
    
    logger.info("Bot started successfully!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
