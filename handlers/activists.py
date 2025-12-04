from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository, ActivistRepository
from filters import BangCommand

router = Router(name="activists")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class AddActivistStates(StatesGroup):
    """Состояния для добавления активиста."""
    waiting_for_data = State()


@router.message(BangCommand("инфа"))
async def cmd_info(message: Message, session: AsyncSession, command_args: str):
    """!инфа [фамилия/юзернейм] — инфа об активисте."""
    if not command_args:
        await message.answer(
            "❌ Укажи фамилию или юзернейм!\n"
            "Пример: <code>!инфа Иванов</code> или <code>!инфа @username</code>",
            parse_mode="HTML"
        )
        return
    
    chat_repo = ChatRepository(session)
    activist_repo = ActivistRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("❌ В этом чате ещё нет информации об активистах.")
        return
    
    activist = await activist_repo.find_by_query(chat, command_args)
    
    if not activist:
        await message.answer(f"❌ Активист «{command_args}» не найден.")
        return
    
    # Формируем информацию
    info_parts = [f"👤 <b>{activist.full_name}</b>"]
    
    if activist.username:
        info_parts.append(f"📱 @{activist.username}")
    
    if activist.role:
        info_parts.append(f"🎭 Роль: {activist.role}")
    
    if activist.info:
        info_parts.append(f"\n📝 {activist.info}")
    
    await message.answer("\n".join(info_parts), parse_mode="HTML")


@router.message(BangCommand("активист"))
async def cmd_activist_of_day(message: Message, session: AsyncSession, command_args: str):
    """!активист дня — случайный активист дня."""
    if command_args.lower().strip() != "дня":
        return
    
    chat_repo = ChatRepository(session)
    activist_repo = ActivistRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("❌ В этом чате ещё нет активистов!")
        return
    
    activist = await activist_repo.get_random(chat)
    
    if not activist:
        await message.answer("❌ В этом чате ещё нет активистов!")
        return
    
    mention = f"@{activist.username}" if activist.username else activist.full_name
    
    # Для тренерского чата - "тренер дня"
    if chat.chat_type == "trainer":
        title = "Тренер дня"
        congrats = f"Поздравляем, {activist.full_name}! Сегодня ты лучший тренер!"
    else:
        title = "Активист дня"
        congrats = f"Поздравляем, {activist.full_name}! Сегодня ты главный!"
    
    await message.answer(
        f"🎉 <b>{title}:</b> {mention}\n\n{congrats}",
        parse_mode="HTML"
    )


@router.message(BangCommand("тренер"))
async def cmd_trainer_of_day(message: Message, session: AsyncSession, command_args: str):
    """!тренер дня — случайный тренер дня (для тренерских чатов)."""
    if command_args.lower().strip() != "дня":
        return
    
    chat_repo = ChatRepository(session)
    activist_repo = ActivistRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("❌ В этом чате ещё нет тренеров!")
        return
    
    activist = await activist_repo.get_random(chat)
    
    if not activist:
        await message.answer("❌ В этом чате ещё нет тренеров!")
        return
    
    mention = f"@{activist.username}" if activist.username else activist.full_name
    
    await message.answer(
        f"🏋️ <b>Тренер дня:</b> {mention}\n\n"
        f"Поздравляем, {activist.full_name}! Сегодня ты лучший тренер!",
        parse_mode="HTML"
    )


@router.message(BangCommand("скрипач"))
async def cmd_skripach_of_day(message: Message, session: AsyncSession, command_args: str):
    """!скрипач дня — случайный скрипач дня (для тренерских чатов)."""
    if command_args.lower().strip() != "дня":
        return
    
    chat_repo = ChatRepository(session)
    activist_repo = ActivistRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("❌ В этом чате ещё нет тренеров!")
        return
    
    # Только для тренерских чатов
    if chat.chat_type != "trainer":
        await message.answer("🎻 Эта команда доступна только в тренерском чате!")
        return
    
    activist = await activist_repo.get_random(chat)
    
    if not activist:
        await message.answer("❌ В этом чате ещё нет тренеров!")
        return
    
    mention = f"@{activist.username}" if activist.username else activist.full_name
    
    await message.answer(
        f"🎻 <b>Скрипач дня:</b> {mention}\n\n"
        f"{activist.full_name}, сегодня ты наш скрипач! 🎶",
        parse_mode="HTML"
    )


@router.message(Command("add_activist"))
async def cmd_add_activist_start(message: Message, state: FSMContext):
    """Начать добавление активиста (админ-команда)."""
    # Проверяем права администратора
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ("administrator", "creator"):
        await message.answer("❌ Только администраторы могут добавлять активистов!")
        return
    
    await message.answer(
        "📝 Отправь информацию об активисте в формате:\n\n"
        "<code>Имя Фамилия\n"
        "@username (опционально)\n"
        "Роль (опционально)\n"
        "Описание (опционально)</code>\n\n"
        "Пример:\n"
        "<code>Иван Иванов\n"
        "@ivanov\n"
        "Председатель\n"
        "Самый активный участник</code>\n\n"
        "Или /cancel для отмены",
        parse_mode="HTML"
    )
    await state.set_state(AddActivistStates.waiting_for_data)


@router.message(AddActivistStates.waiting_for_data, Command("cancel"))
async def cmd_cancel_add_activist(message: Message, state: FSMContext):
    """Отмена добавления активиста."""
    await state.clear()
    await message.answer("❌ Добавление активиста отменено.")


@router.message(AddActivistStates.waiting_for_data)
async def process_activist_data(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка данных активиста."""
    lines = message.text.strip().split("\n")
    
    if len(lines) < 1:
        await message.answer("❌ Минимум укажи имя и фамилию!")
        return
    
    full_name = lines[0].strip()
    name_parts = full_name.split()
    surname = name_parts[-1] if len(name_parts) > 1 else None
    
    username = None
    role = None
    info = None
    
    for i, line in enumerate(lines[1:], 1):
        line = line.strip()
        if line.startswith("@"):
            username = line[1:]
        elif i == 2 and not line.startswith("@"):
            role = line
        elif i >= 3 or (i == 2 and role):
            if info:
                info += "\n" + line
            else:
                info = line
    
    chat_repo = ChatRepository(session)
    activist_repo = ActivistRepository(session)
    
    chat = await chat_repo.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title
    )
    
    activist = await activist_repo.add(
        chat=chat,
        full_name=full_name,
        surname=surname,
        username=username,
        role=role,
        info=info,
    )
    
    await state.clear()
    await message.answer(
        f"✅ Активист добавлен!\n\n"
        f"👤 {activist.full_name}\n"
        f"{'📱 @' + activist.username if activist.username else ''}\n"
        f"{'🎭 ' + activist.role if activist.role else ''}",
        parse_mode="HTML"
    )

