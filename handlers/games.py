import random
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository, MutedUserRepository, MathDuelRepository
from filters import BangCommand

router = Router(name="games")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

MUTE_DURATION_MINUTES = 10


async def mute_user(bot: Bot, chat_id: int, user_id: int, duration_minutes: int) -> bool:
    """Замутить пользователя на указанное количество минут."""
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


async def unmute_user(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Размутить пользователя."""
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        return True
    except TelegramBadRequest:
        return False


@router.message(BangCommand("рулетка"))
async def cmd_roulette(message: Message, session: AsyncSession, command_args: str):
    """!рулетка — шанс 1/6 получить мут на 10 мин."""
    roll = random.randint(1, 6)
    
    if roll == 1:
        # Неудача - мут!
        muted = await mute_user(
            message.bot,
            message.chat.id,
            message.from_user.id,
            MUTE_DURATION_MINUTES
        )
        
        if muted:
            # Сохраняем в БД
            chat_repo = ChatRepository(session)
            muted_repo = MutedUserRepository(session)
            
            chat = await chat_repo.get_or_create(message.chat.id, message.chat.title)
            await muted_repo.add(
                chat=chat,
                user_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                muted_until=datetime.now() + timedelta(minutes=MUTE_DURATION_MINUTES),
                reason="рулетка",
            )
            
            await message.answer(
                f"🔫 БАХ! {message.from_user.full_name} выбил 1 из 6!\n"
                f"🔇 Мут на {MUTE_DURATION_MINUTES} минут!",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"🔫 БАХ! {message.from_user.full_name} выбил 1 из 6!\n"
                f"😅 Но у меня нет прав на мут...",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            f"🔫 *клик* — {message.from_user.full_name} выбил {roll} из 6.\n"
            f"😮‍💨 Повезло!",
            parse_mode="HTML"
        )


@router.message(BangCommand("дуель"))
async def cmd_duel(message: Message, session: AsyncSession, command_args: str):
    """!дуель (в ответ) — рандомный мут на 10 мин."""
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("❌ Ответь на сообщение того, с кем хочешь дуэль!")
        return
    
    opponent = message.reply_to_message.from_user
    challenger = message.from_user
    
    if opponent.id == challenger.id:
        await message.answer("❌ Нельзя дуэлить самого себя!")
        return
    
    if opponent.is_bot:
        await message.answer("❌ Нельзя дуэлить бота!")
        return
    
    # Рандомный победитель
    winner, loser = random.choice([
        (challenger, opponent),
        (opponent, challenger)
    ])
    
    muted = await mute_user(
        message.bot,
        message.chat.id,
        loser.id,
        MUTE_DURATION_MINUTES
    )
    
    if muted:
        # Сохраняем в БД
        chat_repo = ChatRepository(session)
        muted_repo = MutedUserRepository(session)
        
        chat = await chat_repo.get_or_create(message.chat.id, message.chat.title)
        await muted_repo.add(
            chat=chat,
            user_id=loser.id,
            username=loser.username,
            full_name=loser.full_name,
            muted_until=datetime.now() + timedelta(minutes=MUTE_DURATION_MINUTES),
            reason=f"дуэль с {winner.full_name}",
        )
        
        await message.answer(
            f"⚔️ <b>ДУЭЛЬ!</b>\n\n"
            f"🆚 {challenger.full_name} vs {opponent.full_name}\n\n"
            f"🏆 Победитель: <b>{winner.full_name}</b>!\n"
            f"🔇 {loser.full_name} в муте на {MUTE_DURATION_MINUTES} минут!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⚔️ <b>ДУЭЛЬ!</b>\n\n"
            f"🆚 {challenger.full_name} vs {opponent.full_name}\n\n"
            f"🏆 Победитель: <b>{winner.full_name}</b>!\n"
            f"😅 Но у меня нет прав на мут {loser.full_name}...",
            parse_mode="HTML"
        )


@router.message(BangCommand("анмут"))
async def cmd_unmute_all(message: Message, session: AsyncSession, command_args: str):
    """!анмут — размутить всех в муте."""
    chat_repo = ChatRepository(session)
    muted_repo = MutedUserRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("✅ Никто не в муте!")
        return
    
    muted_users = await muted_repo.get_active_mutes(chat)
    
    if not muted_users:
        await message.answer("✅ Никто не в муте!")
        return
    
    unmuted_count = 0
    for muted in muted_users:
        if await unmute_user(message.bot, message.chat.id, muted.user_id):
            unmuted_count += 1
    
    # Удаляем записи о мутах
    await muted_repo.remove_all(chat)
    
    await message.answer(f"✅ Размучено пользователей: {unmuted_count}")

