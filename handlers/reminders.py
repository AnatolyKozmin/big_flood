import re
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository, ReminderRepository
from filters import BangCommand

router = Router(name="reminders")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Паттерн для парсинга даты и времени: DD.MM.YYYY HH:MM
DATE_TIME_PATTERN = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})")


@router.message(BangCommand("разбудить"))
async def cmd_remind(message: Message, session: AsyncSession, command_args: str):
    """!разбудить DD.MM.YYYY HH:MM [текст] — напоминание в чате."""
    if not command_args:
        await message.answer(
            "❌ Укажи дату и время!\n"
            "Формат: <code>!разбудить DD.MM.YYYY HH:MM текст</code>\n"
            "Пример: <code>!разбудить 25.12.2025 10:00 С Новым годом!</code>",
            parse_mode="HTML"
        )
        return
    
    match = DATE_TIME_PATTERN.match(command_args)
    if not match:
        await message.answer(
            "❌ Неверный формат даты!\n"
            "Формат: <code>!разбудить DD.MM.YYYY HH:MM текст</code>\n"
            "Пример: <code>!разбудить 25.12.2025 10:00</code>",
            parse_mode="HTML"
        )
        return
    
    day, month, year, hour, minute = map(int, match.groups())
    
    try:
        remind_at = datetime(year, month, day, hour, minute)
    except ValueError:
        await message.answer("❌ Некорректная дата или время!")
        return
    
    if remind_at <= datetime.now():
        await message.answer("❌ Нельзя установить напоминание в прошлое!")
        return
    
    # Текст после даты-времени
    reminder_text = command_args[match.end():].strip() or None
    
    chat_repo = ChatRepository(session)
    reminder_repo = ReminderRepository(session)
    
    chat = await chat_repo.get_or_create(message.chat.id, message.chat.title)
    
    reminder = await reminder_repo.add(
        chat=chat,
        remind_at=remind_at,
        created_by_id=message.from_user.id,
        created_by_name=message.from_user.full_name,
        text=reminder_text,
    )
    
    text_preview = f"\n📝 Текст: {reminder_text}" if reminder_text else ""
    
    await message.answer(
        f"⏰ Напоминание #{reminder.id} установлено!\n"
        f"📅 Дата: {remind_at.strftime('%d.%m.%Y %H:%M')}"
        f"{text_preview}",
        parse_mode="HTML"
    )

