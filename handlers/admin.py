import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import async_session
from database.repositories import ChatRepository

logger = logging.getLogger(__name__)

router = Router(name="admin")

# ID администраторов бота (добавь сюда свой user_id)
# Узнать можно написав боту /my_id
ADMIN_IDS = set()  # Будет заполняться динамически


class AdminStates(StatesGroup):
    waiting_chat_id = State()


# === Команды для всех (в группах) ===

@router.message(Command("chat_id_blin"))
async def cmd_chat_id(message: Message):
    """Показать ID текущего чата."""
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            f"🆔 <b>ID этого чата:</b>\n\n"
            f"<code>{message.chat.id}</code>\n\n"
            f"Скопируй и отправь админу бота!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🆔 <b>Твой user ID:</b> <code>{message.from_user.id}</code>",
            parse_mode="HTML"
        )


@router.message(Command("my_id"))
async def cmd_my_id(message: Message):
    """Показать свой user_id."""
    await message.answer(
        f"🆔 <b>Твой user ID:</b> <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


@router.message(Command("ping"), F.chat.type == "private")
async def cmd_ping(message: Message):
    """Тест - бот живой?"""
    logger.info(f"PING from {message.from_user.id}")
    await message.answer("🏓 Pong!")


# === Админка в ЛС ===

@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin_panel(message: Message, state: FSMContext):
    """Админ-панель в ЛС."""
    await state.clear()
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Команды:\n"
        "• <code>/set_trainer</code> — сделать чат тренерским\n"
        "• <code>/set_default</code> — сделать чат обычным\n"
        "• <code>/chat_info [chat_id]</code> — инфо о чате\n\n"
        "Чтобы узнать ID чата, напиши в группе: /chat_id_blin",
        parse_mode="HTML"
    )


@router.message(Command("cancel"), F.chat.type == "private")
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🤷 Нечего отменять.")
        return
    
    await state.clear()
    await message.answer("❌ Действие отменено.")


@router.message(Command("set_trainer"), F.chat.type == "private")
async def cmd_set_trainer(message: Message, state: FSMContext):
    """Начать процесс установки тренерского чата."""
    await message.answer(
        "📝 Отправь ID чата, который нужно сделать <b>тренерским</b>:\n\n"
        "<i>Чтобы узнать ID, напиши в группе /chat_id_blin</i>\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_chat_id)
    await state.update_data(action="trainer")


@router.message(Command("set_default"), F.chat.type == "private")
async def cmd_set_default(message: Message, state: FSMContext):
    """Начать процесс установки обычного чата."""
    await message.answer(
        "📝 Отправь ID чата, который нужно сделать <b>обычным</b>:\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_chat_id)
    await state.update_data(action="default")


@router.message(AdminStates.waiting_chat_id, F.chat.type == "private")
async def process_chat_id(message: Message, state: FSMContext):
    """Обработка ID чата."""
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Это не похоже на ID чата. Отправь число.")
        return
    
    data = await state.get_data()
    action = data.get("action", "default")
    
    chat_type = "trainer" if action == "trainer" else "default"
    type_name = "тренерский 🏋️" if action == "trainer" else "обычный"
    
    async with async_session() as session:
        chat_repo = ChatRepository(session)
        chat = await chat_repo.set_chat_type(chat_id, chat_type)
        
        if chat:
            await message.answer(
                f"✅ Чат успешно обновлён!\n\n"
                f"🆔 ID: <code>{chat_id}</code>\n"
                f"📝 Название: {chat.title or 'Неизвестно'}\n"
                f"🏷 Тип: <b>{type_name}</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"❌ Чат с ID <code>{chat_id}</code> не найден в базе.\n\n"
                f"Бот должен сначала быть добавлен в этот чат!",
                parse_mode="HTML"
            )
    
    await state.clear()


@router.message(Command("chat_info"), F.chat.type == "private")
async def cmd_chat_info(message: Message, state: FSMContext):
    """Информация о чате по ID."""
    logger.info(f"chat_info called by {message.from_user.id}, text: {message.text}")
    
    # Очищаем состояние если было
    await state.clear()
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ Укажи ID чата: <code>/chat_info -123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        chat_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ Некорректный ID чата.")
        return
    
    async with async_session() as session:
        chat_repo = ChatRepository(session)
        chat = await chat_repo.get_by_chat_id(chat_id)
        
        if chat:
            type_name = "тренерский 🏋️" if chat.chat_type == "trainer" else "обычный"
            await message.answer(
                f"📊 <b>Информация о чате:</b>\n\n"
                f"🆔 ID: <code>{chat.chat_id}</code>\n"
                f"📝 Название: {chat.title or 'Неизвестно'}\n"
                f"🏷 Тип: <b>{type_name}</b>\n"
                f"📅 Добавлен: {chat.created_at.strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML"
            )
        else:
            await message.answer(f"❌ Чат с ID <code>{chat_id}</code> не найден.", parse_mode="HTML")

