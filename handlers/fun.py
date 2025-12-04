import random
import hashlib
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository
from filters import BangCommand

router = Router(name="fun")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Дата дедлайна (по МСК)
TARGET_DATE = datetime(2025, 11, 27, 0, 0, 0)

# Ответы для !нахуй
NAHUI_RESPONSES = [
    "Иди нахуй, {name}! 🖕",
    "{name}, нахуй пошёл! 😤",
    "Нахуй тебя, {name}! 🚀",
    "{name} 👉 нахуй 👈",
    "Слышь, {name}, иди нахуй! 💀",
    "{name}, вали нахуй отсюда! 🌚",
    "🖕 {name} 🖕",
    "{name}, тебе туда → 🚪",
    "Эй, {name}, нахуй иди! 🚶",
    "{name}, пошёл нахуй! 👋",
]

# Ответы для !обосновать
OBOSNOVAT_RESPONSES = [
    "А тебе это ебать не должно 😎",
    "А тебе это ебать не должно, {name} 🤷",
    "Тебе это ебать не должно! 💅",
    "{name}, а тебе это ебать не должно 😏",
    "Короче, {name}, тебе это ебать не должно 🙄",
    "А с хуя ли тебе это должно ебать, {name}? 🤔",
    "Тебя это ебать не должно от слова совсем 💀",
    "{name}, тебе не похуй? Должно быть похуй 😌",
]


@router.message(BangCommand("нахуй"))
async def cmd_nahui(message: Message, command_args: str):
    """!нахуй (в ответ) — адресный ответ на сообщение."""
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение того, кого посылаешь!")
        return
    
    target = message.reply_to_message.from_user
    
    if target and target.is_bot:
        await message.answer("❌ Ботов нахуй не посылают! 🤖")
        return
    
    target_name = target.full_name if target else "Аноним"
    response = random.choice(NAHUI_RESPONSES).format(name=target_name)
    
    # Отвечаем на то сообщение, на которое ответил пользователь
    await message.reply_to_message.reply(response)


@router.message(BangCommand("обосновать"))
async def cmd_obosnovat(message: Message, command_args: str):
    """!обосновать (в ответ) — адресный ответ на сообщение."""
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение того, кого обосновываешь!")
        return
    
    target = message.reply_to_message.from_user
    target_name = target.full_name if target else "Аноним"
    response = random.choice(OBOSNOVAT_RESPONSES).format(name=target_name)
    
    # Отвечаем на то сообщение, на которое ответил пользователь
    await message.reply_to_message.reply(response)


@router.message(BangCommand("когда"))
async def cmd_when(message: Message, command_args: str):
    """!когда — сколько осталось до 27.11.2025."""
    from utils.timezone import get_moscow_now
    
    now = get_moscow_now()
    
    if now >= TARGET_DATE:
        await message.answer("🎉 27.11.2025 уже наступило!")
        return
    
    delta = TARGET_DATE - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    await message.answer(
        f"⏳ <b>До 27.11.2025 осталось:</b>\n\n"
        f"📅 {days} дней\n"
        f"🕐 {hours} часов\n"
        f"⏱ {minutes} минут\n"
        f"⏰ {seconds} секунд",
        parse_mode="HTML"
    )


@router.message(BangCommand("вероятность"))
async def cmd_probability(message: Message, command_args: str):
    """!вероятность [событие] — шанс в процентах."""
    if not command_args:
        await message.answer(
            "❌ Укажи событие!\n"
            "Пример: <code>!вероятность что завтра будет дождь</code>",
            parse_mode="HTML"
        )
        return
    
    # Генерируем "стабильный" рандом на основе хэша события + дня
    today = datetime.now().strftime("%Y-%m-%d")
    seed_string = f"{command_args.lower()}{today}{message.chat.id}"
    hash_value = int(hashlib.md5(seed_string.encode()).hexdigest(), 16)
    probability = hash_value % 101  # 0-100%
    
    # Эмодзи в зависимости от вероятности
    if probability <= 10:
        emoji = "😢"
    elif probability <= 30:
        emoji = "😕"
    elif probability <= 50:
        emoji = "🤔"
    elif probability <= 70:
        emoji = "😊"
    elif probability <= 90:
        emoji = "😃"
    else:
        emoji = "🎉"
    
    await message.answer(
        f"🎲 Вероятность того, что <i>{command_args}</i>:\n\n"
        f"<b>{probability}%</b> {emoji}",
        parse_mode="HTML"
    )


@router.message(BangCommand("кто"))
async def cmd_who(message: Message, session: AsyncSession, command_args: str):
    """!кто [текст] — случайный человек из участников чата."""
    if not command_args:
        await message.answer(
            "❌ Укажи текст!\n"
            "Пример: <code>!кто сегодня красавчик</code>",
            parse_mode="HTML"
        )
        return
    
    # Сначала пробуем из Redis кэша (быстро)
    from cache.chat_members import ChatMembersCache
    
    cached_member = await ChatMembersCache.get_random_member(message.chat.id)
    
    if cached_member:
        if cached_member.username:
            mention = f"@{cached_member.username}"
        else:
            mention = f'<a href="tg://user?id={cached_member.user_id}">{cached_member.full_name}</a>'
        
        await message.answer(
            f"🎯 <b>{command_args}:</b>\n\n"
            f"👉 {mention}",
            parse_mode="HTML"
        )
        return
    
    # Если кэш пуст - идём в БД
    from database.repositories import ChatMemberRepository
    
    chat_repo = ChatRepository(session)
    member_repo = ChatMemberRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("❌ В этом чате ещё никто не писал!")
        return
    
    member = await member_repo.get_random(chat)
    
    if not member:
        await message.answer("❌ В этом чате ещё никто не писал!")
        return
    
    if member.username:
        mention = f"@{member.username}"
    else:
        mention = f'<a href="tg://user?id={member.user_id}">{member.full_name}</a>'
    
    await message.answer(
        f"🎯 <b>{command_args}:</b>\n\n"
        f"👉 {mention}",
        parse_mode="HTML"
    )

