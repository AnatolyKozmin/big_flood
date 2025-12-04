import random
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository, MutedUserRepository, MathDuelRepository
from filters import BangCommand

router = Router(name="math_duel")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

DUEL_DURATION_MINUTES = 10
MUTE_DURATION_MINUTES = 10


def generate_math_problem() -> tuple[str, int]:
    """Генерировать математическую задачу. Возвращает (выражение, ответ)."""
    operations = [
        ("сложение", lambda a, b: (f"{a} + {b}", a + b)),
        ("вычитание", lambda a, b: (f"{a} - {b}", a - b)),
        ("умножение", lambda a, b: (f"{a} × {b}", a * b)),
        ("деление", lambda a, b: (f"{a * b} ÷ {a}", b)),  # Гарантируем целый результат
    ]
    
    op_name, op_func = random.choice(operations)
    
    if op_name == "умножение":
        a = random.randint(2, 15)
        b = random.randint(2, 15)
    elif op_name == "деление":
        a = random.randint(2, 12)
        b = random.randint(2, 12)
    else:
        a = random.randint(10, 100)
        b = random.randint(10, 100)
    
    expression, answer = op_func(a, b)
    return expression, answer


async def mute_user(bot: Bot, chat_id: int, user_id: int, duration_minutes: int) -> bool:
    """Замутить пользователя."""
    try:
        until_date = datetime.now() + timedelta(minutes=duration_minutes)
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        return True
    except TelegramBadRequest:
        return False


@router.message(BangCommand("матдуэль"))
async def cmd_math_duel(message: Message, session: AsyncSession, command_args: str):
    """!матдуэль (в ответ) — математическая дуэль."""
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("❌ Ответь на сообщение того, с кем хочешь матдуэль!")
        return
    
    opponent = message.reply_to_message.from_user
    challenger = message.from_user
    
    if opponent.id == challenger.id:
        await message.answer("❌ Нельзя дуэлить самого себя!")
        return
    
    if opponent.is_bot:
        await message.answer("❌ Нельзя дуэлить бота!")
        return
    
    chat_repo = ChatRepository(session)
    duel_repo = MathDuelRepository(session)
    
    chat = await chat_repo.get_or_create(message.chat.id, message.chat.title)
    
    # Проверяем, нет ли уже активной дуэли у участников
    existing_duel = await duel_repo.get_active_for_user(chat, challenger.id)
    if existing_duel:
        await message.answer("❌ У тебя уже есть активная дуэль! Сначала заверши её.")
        return
    
    existing_duel = await duel_repo.get_active_for_user(chat, opponent.id)
    if existing_duel:
        await message.answer(f"❌ У {opponent.full_name} уже есть активная дуэль!")
        return
    
    # Генерируем задачу
    expression, answer = generate_math_problem()
    expires_at = datetime.now() + timedelta(minutes=DUEL_DURATION_MINUTES)
    
    # Создаём дуэль
    duel = await duel_repo.create(
        chat=chat,
        challenger_id=challenger.id,
        challenger_name=challenger.full_name,
        opponent_id=opponent.id,
        opponent_name=opponent.full_name,
        expression=expression,
        answer=answer,
        expires_at=expires_at,
    )
    
    await message.answer(
        f"🧮 <b>МАТДУЭЛЬ!</b>\n\n"
        f"⚔️ {challenger.full_name} vs {opponent.full_name}\n\n"
        f"📝 <b>Задача:</b> {expression} = ?\n\n"
        f"Кто первый напишет правильный ответ — победит!\n"
        f"Проигравший получит мут на {MUTE_DURATION_MINUTES} минут.\n\n"
        f"⏱ Дуэль истекает через {DUEL_DURATION_MINUTES} минут.",
        parse_mode="HTML"
    )


@router.message(F.text.regexp(r"^-?\d+$"))
async def check_math_answer(message: Message, session: AsyncSession):
    """Проверка ответа на математическую дуэль."""
    chat_repo = ChatRepository(session)
    duel_repo = MathDuelRepository(session)
    muted_repo = MutedUserRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        return
    
    # Ищем активную дуэль, где участвует пользователь
    duel = await duel_repo.get_active_for_user(chat, message.from_user.id)
    if not duel:
        return
    
    # Проверяем ответ
    try:
        user_answer = int(message.text.strip())
    except ValueError:
        return
    
    if user_answer != duel.answer:
        return  # Неправильный ответ — просто игнорируем
    
    # Правильный ответ!
    winner_id = message.from_user.id
    loser_id = duel.opponent_id if duel.challenger_id == winner_id else duel.challenger_id
    winner_name = message.from_user.full_name
    loser_name = duel.opponent_name if duel.challenger_id == winner_id else duel.challenger_name
    
    # Завершаем дуэль
    await duel_repo.finish_duel(duel, winner_id)
    
    # Мутим проигравшего
    muted = await mute_user(
        message.bot,
        message.chat.id,
        loser_id,
        MUTE_DURATION_MINUTES
    )
    
    if muted:
        await muted_repo.add(
            chat=chat,
            user_id=loser_id,
            muted_until=datetime.now() + timedelta(minutes=MUTE_DURATION_MINUTES),
            reason=f"проиграл матдуэль {winner_name}",
        )
        
        await message.answer(
            f"🎉 <b>ПОБЕДА!</b>\n\n"
            f"🏆 {winner_name} первым решил: {duel.expression} = <b>{duel.answer}</b>\n\n"
            f"🔇 {loser_name} в муте на {MUTE_DURATION_MINUTES} минут!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🎉 <b>ПОБЕДА!</b>\n\n"
            f"🏆 {winner_name} первым решил: {duel.expression} = <b>{duel.answer}</b>\n\n"
            f"😅 Но у меня нет прав на мут {loser_name}...",
            parse_mode="HTML"
        )

