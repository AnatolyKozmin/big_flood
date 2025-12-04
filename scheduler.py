import asyncio
import logging
from datetime import datetime

from aiogram import Bot

from database.engine import async_session
from database.repositories import ReminderRepository, MathDuelRepository
from database.models import Chat

logger = logging.getLogger(__name__)


async def check_reminders(bot: Bot):
    """Проверяет и отправляет напоминания."""
    async with async_session() as session:
        reminder_repo = ReminderRepository(session)
        
        # Получаем все непосланные напоминания до текущего момента
        reminders = await reminder_repo.get_pending(datetime.now())
        
        for reminder in reminders:
            try:
                # Получаем chat_id из связанного чата
                from sqlalchemy import select
                from database.models import Chat
                
                stmt = select(Chat).where(Chat.id == reminder.chat_pk)
                result = await session.execute(stmt)
                chat = result.scalar_one_or_none()
                
                if not chat:
                    continue
                
                text_part = f"\n\n📝 {reminder.text}" if reminder.text else ""
                message = (
                    f"⏰ <b>НАПОМИНАНИЕ!</b>{text_part}\n\n"
                    f"👤 Создано: {reminder.created_by_name or 'Аноним'}"
                )
                
                await bot.send_message(
                    chat_id=chat.chat_id,
                    text=message,
                    parse_mode="HTML"
                )
                
                await reminder_repo.mark_sent(reminder)
                logger.info(f"Sent reminder #{reminder.id} to chat {chat.chat_id}")
                
            except Exception as e:
                logger.error(f"Error sending reminder #{reminder.id}: {e}")


async def expire_duels():
    """Завершает истекшие матдуэли."""
    async with async_session() as session:
        duel_repo = MathDuelRepository(session)
        expired = await duel_repo.expire_old_duels()
        if expired:
            logger.info(f"Expired {expired} math duels")


async def scheduler_loop(bot: Bot):
    """Основной цикл планировщика."""
    logger.info("Scheduler started")
    
    while True:
        try:
            await check_reminders(bot)
            await expire_duels()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)

