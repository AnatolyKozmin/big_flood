"""
Админ-панель бота с inline кнопками.

Функционал:
- Управление чатами (тип чата, настройки)
- Привязка Google Sheets для импорта активистов
- Загрузка плашек для цитат
- Синхронизация данных
"""

import logging
from datetime import datetime
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.engine import async_session
from database.repositories import ChatRepository, ActivistRepository
from services.google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)

router = Router(name="admin")


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    waiting_chat_id = State()
    waiting_sheet_url = State()
    waiting_template = State()
    selecting_chat = State()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def build_main_menu_keyboard():
    """Клавиатура главного меню админки."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои чаты", callback_data="admin:chats")
    builder.button(text="📊 Импорт из таблицы", callback_data="admin:import")
    builder.button(text="🖼 Плашки для цитат", callback_data="admin:templates")
    builder.button(text="❓ Помощь", callback_data="admin:help")
    builder.adjust(2, 2)
    return builder.as_markup()


def build_chat_list_keyboard(chats: list, action: str = "view"):
    """Клавиатура со списком чатов."""
    builder = InlineKeyboardBuilder()
    
    for chat in chats:
        title = chat.title or f"Чат {chat.chat_id}"
        if len(title) > 25:
            title = title[:22] + "..."
        
        type_emoji = "🏋️" if chat.chat_type == "trainer" else "👥"
        builder.button(
            text=f"{type_emoji} {title}",
            callback_data=f"chat:{action}:{chat.id}"
        )
    
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def build_chat_settings_keyboard(chat_id: int, chat_type: str):
    """Клавиатура настроек конкретного чата."""
    builder = InlineKeyboardBuilder()
    
    # Переключатель типа чата
    if chat_type == "trainer":
        builder.button(text="👥 Сделать обычным", callback_data=f"chat:settype:{chat_id}:default")
    else:
        builder.button(text="🏋️ Сделать тренерским", callback_data=f"chat:settype:{chat_id}:trainer")
    
    builder.button(text="📊 Привязать таблицу", callback_data=f"chat:sheet:{chat_id}")
    builder.button(text="🔄 Синхронизировать", callback_data=f"chat:sync:{chat_id}")
    builder.button(text="🖼 Загрузить плашку", callback_data=f"chat:template:{chat_id}")
    builder.button(text="📋 Список активистов", callback_data=f"chat:activists:{chat_id}")
    builder.button(text="🗑 Очистить активистов", callback_data=f"chat:clear:{chat_id}")
    builder.button(text="◀️ К списку чатов", callback_data="admin:chats")
    
    builder.adjust(1)
    return builder.as_markup()


def build_back_keyboard(callback_data: str = "admin:menu"):
    """Клавиатура с кнопкой назад."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=callback_data)
    return builder.as_markup()


def build_confirm_keyboard(action: str, chat_id: int):
    """Клавиатура подтверждения."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=f"confirm:{action}:{chat_id}")
    builder.button(text="❌ Нет", callback_data=f"chat:view:{chat_id}")
    builder.adjust(2)
    return builder.as_markup()


# ============================================
# КОМАНДЫ ДЛЯ ВСЕХ (в группах)
# ============================================

@router.message(Command("chat_id_blin"))
async def cmd_chat_id(message: Message):
    """Показать ID текущего чата."""
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            f"🆔 <b>ID этого чата:</b>\n\n"
            f"<code>{message.chat.id}</code>\n\n"
            f"Скопируй и отправь в ЛС боту для настройки!",
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


# ============================================
# АДМИНКА В ЛС - ГЛАВНОЕ МЕНЮ
# ============================================

@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin_panel(message: Message, state: FSMContext):
    """Админ-панель в ЛС."""
    await state.clear()
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=build_main_menu_keyboard()
    )


@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие в ЛС."""
    await state.clear()
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для групповых чатов.\n\n"
        "📝 Чтобы настроить меня для своей группы:\n"
        "1. Добавь меня в группу\n"
        "2. Напиши /chat_id_blin в группе\n"
        "3. Вернись сюда и нажми /admin\n\n"
        "Используй /admin для открытия админ-панели.",
        parse_mode="HTML",
        reply_markup=build_main_menu_keyboard()
    )


@router.message(Command("cancel"), F.chat.type == "private")
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🤷 Нечего отменять.")
        return
    
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=build_main_menu_keyboard()
    )


# ============================================
# CALLBACK HANDLERS - НАВИГАЦИЯ
# ============================================

@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=build_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:help")
async def cb_admin_help(callback: CallbackQuery):
    """Справка по админке."""
    help_text = """
📖 <b>Справка по админ-панели</b>

<b>📋 Мои чаты</b>
Список всех чатов, где есть бот. Можно настраивать тип чата и другие параметры.

<b>📊 Импорт из таблицы</b>
Импортировать активистов из Google Таблицы.

<b>Формат таблицы (6 колонок):</b>
• A: ФИО (обязательно)
• B: Юзернейм в тг (обязательно, без @)
• C: Группа
• D: Номер телефона
• E: Есть права
• F: Адрес

⚠️ Таблица должна быть <b>публичной</b>!
Строки без ФИО или юзернейма пропускаются.

<b>🖼 Плашки для цитат</b>
Загрузить фоновое изображение для цитат.
Рекомендуемый размер: 800x600 px

<b>Типы чатов:</b>
👥 Обычный — активисты
🏋️ Тренерский — тренеры
"""
    await callback.message.edit_text(
        help_text,
        parse_mode="HTML",
        reply_markup=build_back_keyboard()
    )
    await callback.answer()


# ============================================
# СПИСОК ЧАТОВ
# ============================================

@router.callback_query(F.data == "admin:chats")
async def cb_chat_list(callback: CallbackQuery):
    """Показать список чатов."""
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).order_by(Chat.created_at.desc())
        result = await session.execute(stmt)
        chats = result.scalars().all()
    
    if not chats:
        await callback.message.edit_text(
            "📭 У тебя ещё нет чатов.\n\n"
            "Добавь бота в группу и напиши там /chat_id_blin",
            parse_mode="HTML",
            reply_markup=build_back_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📋 <b>Твои чаты ({len(chats)}):</b>\n\n"
        "Выбери чат для настройки:",
        parse_mode="HTML",
        reply_markup=build_chat_list_keyboard(list(chats), "view")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chat:view:"))
async def cb_chat_view(callback: CallbackQuery):
    """Просмотр настроек чата."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        chat_repo = ChatRepository(session)
        activist_repo = ActivistRepository(session)
        
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await callback.answer("❌ Чат не найден", show_alert=True)
            return
        
        activists = await activist_repo.get_all(chat)
    
    type_name = "🏋️ Тренерский" if chat.chat_type == "trainer" else "👥 Обычный"
    sheet_status = "✅ Привязана" if chat.google_sheet_url else "❌ Не привязана"
    template_status = "✅ Загружена" if chat.quote_template_path else "❌ Не загружена"
    
    synced_text = ""
    if chat.google_sheet_synced_at:
        synced_text = f"\n📅 Синхронизация: {chat.google_sheet_synced_at.strftime('%d.%m.%Y %H:%M')}"
    
    await callback.message.edit_text(
        f"⚙️ <b>Настройки чата</b>\n\n"
        f"📝 <b>{chat.title or 'Без названия'}</b>\n"
        f"🆔 <code>{chat.chat_id}</code>\n\n"
        f"🏷 Тип: {type_name}\n"
        f"👥 Активистов: {len(activists)}\n"
        f"📊 Таблица: {sheet_status}{synced_text}\n"
        f"🖼 Плашка: {template_status}",
        parse_mode="HTML",
        reply_markup=build_chat_settings_keyboard(chat_pk, chat.chat_type)
    )
    await callback.answer()


# ============================================
# ИЗМЕНЕНИЕ ТИПА ЧАТА
# ============================================

@router.callback_query(F.data.startswith("chat:settype:"))
async def cb_set_chat_type(callback: CallbackQuery):
    """Изменить тип чата."""
    parts = callback.data.split(":")
    chat_pk = int(parts[2])
    new_type = parts[3]
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await callback.answer("❌ Чат не найден", show_alert=True)
            return
        
        chat.chat_type = new_type
        await session.commit()
    
    type_name = "тренерский 🏋️" if new_type == "trainer" else "обычный 👥"
    await callback.answer(f"✅ Тип чата изменён на {type_name}", show_alert=True)
    
    # Обновляем экран
    await cb_chat_view(callback)


# ============================================
# ПРИВЯЗКА GOOGLE SHEETS
# ============================================

@router.callback_query(F.data == "admin:import")
async def cb_import_menu(callback: CallbackQuery):
    """Меню импорта из таблицы."""
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).order_by(Chat.created_at.desc())
        result = await session.execute(stmt)
        chats = result.scalars().all()
    
    if not chats:
        await callback.message.edit_text(
            "📭 Сначала добавь бота в группу.",
            parse_mode="HTML",
            reply_markup=build_back_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📊 <b>Импорт из Google Таблицы</b>\n\n"
        "Выбери чат для импорта активистов:",
        parse_mode="HTML",
        reply_markup=build_chat_list_keyboard(list(chats), "sheet")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chat:sheet:"))
async def cb_chat_sheet(callback: CallbackQuery, state: FSMContext):
    """Привязать таблицу к чату."""
    chat_pk = int(callback.data.split(":")[2])
    
    await state.set_state(AdminStates.waiting_sheet_url)
    await state.update_data(chat_pk=chat_pk)
    
    await callback.message.edit_text(
        "📊 <b>Привязка Google Таблицы</b>\n\n"
        "Отправь ссылку на <b>публичную</b> Google Таблицу.\n\n"
        "<b>Формат таблицы (6 колонок):</b>\n"
        "• A: ФИО (обязательно)\n"
        "• B: Юзернейм в тг (обязательно)\n"
        "• C: Группа\n"
        "• D: Номер телефона\n"
        "• E: Есть права\n"
        "• F: Адрес\n\n"
        "⚠️ Таблица должна быть доступна по ссылке!\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
    )
    await callback.answer()


@router.message(AdminStates.waiting_sheet_url, F.chat.type == "private")
async def process_sheet_url(message: Message, state: FSMContext):
    """Обработка URL таблицы."""
    url = message.text.strip()
    
    if not GoogleSheetsService.validate_url(url):
        await message.answer(
            "❌ Это не похоже на ссылку Google Таблицы.\n\n"
            "Пример: https://docs.google.com/spreadsheets/d/...\n\n"
            "Попробуй ещё раз или /cancel для отмены."
        )
        return
    
    data = await state.get_data()
    chat_pk = data.get("chat_pk")
    
    # Проверяем доступность таблицы
    status_msg = await message.answer("⏳ Проверяю таблицу...")
    
    activists, error = await GoogleSheetsService.fetch_and_parse(url)
    
    if error:
        await status_msg.edit_text(
            f"❌ {error}\n\n"
            "Убедись, что таблица публичная и попробуй снова."
        )
        return
    
    # Сохраняем URL и импортируем данные
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await status_msg.edit_text("❌ Чат не найден.")
            await state.clear()
            return
        
        # Сохраняем URL
        chat.google_sheet_url = url
        chat.google_sheet_synced_at = datetime.now()
        
        # Очищаем старых активистов и добавляем новых
        activist_repo = ActivistRepository(session)
        
        # Удаляем старых
        from sqlalchemy import delete
        from database.models import Activist
        
        await session.execute(delete(Activist).where(Activist.chat_pk == chat_pk))
        
        # Добавляем новых
        for parsed in activists:
            await activist_repo.add(
                chat=chat,
                full_name=parsed.full_name,
                username=parsed.username,
                surname=parsed.surname,
                group_name=parsed.group_name,
                phone=parsed.phone,
                has_license=parsed.has_license,
                address=parsed.address,
            )
        
        await session.commit()
    
    await state.clear()
    await status_msg.edit_text(
        f"✅ <b>Таблица привязана!</b>\n\n"
        f"Импортировано активистов: <b>{len(activists)}</b>\n\n"
        f"Теперь можно использовать команду <code>!инфа</code> в чате.",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
    )


# ============================================
# СИНХРОНИЗАЦИЯ
# ============================================

@router.callback_query(F.data.startswith("chat:sync:"))
async def cb_sync_chat(callback: CallbackQuery):
    """Синхронизировать данные из таблицы."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await callback.answer("❌ Чат не найден", show_alert=True)
            return
        
        if not chat.google_sheet_url:
            await callback.answer("❌ Таблица не привязана", show_alert=True)
            return
        
        await callback.answer("⏳ Синхронизация...")
        
        # Парсим таблицу
        activists, error = await GoogleSheetsService.fetch_and_parse(chat.google_sheet_url)
        
        if error:
            await callback.message.edit_text(
                f"❌ Ошибка синхронизации:\n{error}",
                reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
            )
            return
        
        # Обновляем данные
        activist_repo = ActivistRepository(session)
        
        from sqlalchemy import delete
        from database.models import Activist
        
        await session.execute(delete(Activist).where(Activist.chat_pk == chat_pk))
        
        for parsed in activists:
            await activist_repo.add(
                chat=chat,
                full_name=parsed.full_name,
                username=parsed.username,
                surname=parsed.surname,
                group_name=parsed.group_name,
                phone=parsed.phone,
                has_license=parsed.has_license,
                address=parsed.address,
            )
        
        chat.google_sheet_synced_at = datetime.now()
        await session.commit()
    
    await callback.message.edit_text(
        f"✅ <b>Синхронизация завершена!</b>\n\n"
        f"Обновлено активистов: <b>{len(activists)}</b>",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
    )


# ============================================
# СПИСОК АКТИВИСТОВ
# ============================================

@router.callback_query(F.data.startswith("chat:activists:"))
async def cb_chat_activists(callback: CallbackQuery):
    """Показать список активистов чата."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await callback.answer("❌ Чат не найден", show_alert=True)
            return
        
        activist_repo = ActivistRepository(session)
        activists = await activist_repo.get_all(chat)
    
    if not activists:
        await callback.message.edit_text(
            "📭 В этом чате нет активистов.\n\n"
            "Привяжи Google Таблицу для импорта.",
            parse_mode="HTML",
            reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
        )
        await callback.answer()
        return
    
    # Формируем список
    lines = [f"👥 <b>Активисты ({len(activists)}):</b>\n"]
    
    for i, activist in enumerate(activists[:50], 1):  # Ограничиваем 50
        group_part = f" ({activist.group_name})" if activist.group_name else ""
        lines.append(f"{i}. {activist.full_name} @{activist.username}{group_part}")
    
    if len(activists) > 50:
        lines.append(f"\n<i>...и ещё {len(activists) - 50}</i>")
    
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
    )
    await callback.answer()


# ============================================
# ОЧИСТКА АКТИВИСТОВ
# ============================================

@router.callback_query(F.data.startswith("chat:clear:"))
async def cb_clear_activists_confirm(callback: CallbackQuery):
    """Подтверждение очистки активистов."""
    chat_pk = int(callback.data.split(":")[2])
    
    await callback.message.edit_text(
        "⚠️ <b>Подтверждение</b>\n\n"
        "Удалить всех активистов из этого чата?",
        parse_mode="HTML",
        reply_markup=build_confirm_keyboard("clear", chat_pk)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:clear:"))
async def cb_clear_activists(callback: CallbackQuery):
    """Очистить активистов."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import delete
        from database.models import Activist
        
        result = await session.execute(
            delete(Activist).where(Activist.chat_pk == chat_pk)
        )
        await session.commit()
        deleted = result.rowcount
    
    await callback.answer(f"✅ Удалено: {deleted}", show_alert=True)
    await cb_chat_view(callback)


# ============================================
# ПЛАШКИ ДЛЯ ЦИТАТ
# ============================================

@router.callback_query(F.data == "admin:templates")
async def cb_templates_menu(callback: CallbackQuery):
    """Меню плашек для цитат."""
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).order_by(Chat.created_at.desc())
        result = await session.execute(stmt)
        chats = result.scalars().all()
    
    if not chats:
        await callback.message.edit_text(
            "📭 Сначала добавь бота в группу.",
            reply_markup=build_back_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "🖼 <b>Плашки для цитат</b>\n\n"
        "Выбери чат для загрузки плашки:",
        parse_mode="HTML",
        reply_markup=build_chat_list_keyboard(list(chats), "template")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chat:template:"))
async def cb_chat_template(callback: CallbackQuery, state: FSMContext):
    """Загрузить плашку для чата."""
    chat_pk = int(callback.data.split(":")[2])
    
    await state.set_state(AdminStates.waiting_template)
    await state.update_data(chat_pk=chat_pk)
    
    await callback.message.edit_text(
        "🖼 <b>Загрузка плашки</b>\n\n"
        "Отправь изображение для фона цитат.\n\n"
        "📐 Рекомендуемый размер: 800x600 px\n"
        "📁 Форматы: JPG, PNG\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
    )
    await callback.answer()


@router.message(AdminStates.waiting_template, F.photo, F.chat.type == "private")
async def process_template_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработка загруженной плашки."""
    data = await state.get_data()
    chat_pk = data.get("chat_pk")
    
    # Скачиваем фото
    photo = message.photo[-1]  # Берём самое большое
    file = await bot.get_file(photo.file_id)
    
    # Создаём директорию для шаблонов
    import os
    templates_dir = "assets/templates"
    os.makedirs(templates_dir, exist_ok=True)
    
    # Сохраняем файл
    file_path = f"{templates_dir}/chat_{chat_pk}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    # Обновляем в БД
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.quote_template_path = file_path
            await session.commit()
    
    await state.clear()
    await message.answer(
        "✅ <b>Плашка загружена!</b>\n\n"
        "Теперь цитаты будут генерироваться с этим фоном.",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(f"chat:view:{chat_pk}")
    )


@router.message(AdminStates.waiting_template, F.chat.type == "private")
async def process_template_invalid(message: Message):
    """Неверный формат плашки."""
    await message.answer(
        "❌ Пожалуйста, отправь изображение (фото).\n\n"
        "Для отмены: /cancel"
    )


# ============================================
# КОМАНДЫ ДЛЯ ПРОВЕРКИ БАЗЫ ДАННЫХ
# ============================================

@router.message(Command("db_stats"), F.chat.type == "private")
async def cmd_db_stats(message: Message):
    """Статистика по базе данных."""
    async with async_session() as session:
        from sqlalchemy import select, func
        from database.models import Chat, Activist, Quote, ChatMember
        
        # Считаем статистику
        chats_count = (await session.execute(select(func.count(Chat.id)))).scalar_one()
        activists_count = (await session.execute(select(func.count(Activist.id)))).scalar_one()
        quotes_count = (await session.execute(select(func.count(Quote.id)))).scalar_one()
        members_count = (await session.execute(select(func.count(ChatMember.id)))).scalar_one()
        
        # Получаем чаты с количеством активистов
        stmt = (
            select(Chat, func.count(Activist.id).label('activist_count'))
            .outerjoin(Activist, Chat.id == Activist.chat_pk)
            .group_by(Chat.id)
            .order_by(Chat.created_at.desc())
        )
        result = await session.execute(stmt)
        chat_stats = result.all()
    
    lines = [
        "📊 <b>Статистика базы данных</b>\n",
        f"📋 Всего чатов: <b>{chats_count}</b>",
        f"👥 Всего активистов: <b>{activists_count}</b>",
        f"💬 Всего цитат: <b>{quotes_count}</b>",
        f"👤 Всего участников (трекинг): <b>{members_count}</b>",
        "\n<b>По чатам:</b>\n"
    ]
    
    for chat, activist_count in chat_stats:
        type_emoji = "🏋️" if chat.chat_type == "trainer" else "👥"
        title = chat.title or f"ID: {chat.chat_id}"
        if len(title) > 30:
            title = title[:27] + "..."
        lines.append(f"{type_emoji} {title}: <b>{activist_count}</b> активистов")
    
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("db_activists"), F.chat.type == "private")
async def cmd_db_activists(message: Message):
    """Список всех активистов по чатам."""
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat, Activist
        
        # Получаем все чаты с активистами
        stmt = select(Chat).order_by(Chat.created_at.desc())
        result = await session.execute(stmt)
        chats = result.scalars().all()
    
    if not chats:
        await message.answer("📭 В базе нет чатов.")
        return
    
    for chat in chats:
        async with async_session() as session:
            stmt = select(Activist).where(Activist.chat_pk == chat.id).limit(30)
            result = await session.execute(stmt)
            activists = result.scalars().all()
        
        type_emoji = "🏋️" if chat.chat_type == "trainer" else "👥"
        title = chat.title or f"ID: {chat.chat_id}"
        
        lines = [f"{type_emoji} <b>{title}</b>\n"]
        
        if not activists:
            lines.append("<i>Нет активистов</i>")
        else:
            for i, a in enumerate(activists, 1):
                group_part = f" ({a.group_name})" if a.group_name else ""
                lines.append(f"{i}. {a.full_name} @{a.username}{group_part}")
            
            if len(activists) == 30:
                lines.append("\n<i>...показаны первые 30</i>")
        
        await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("db_check"), F.chat.type == "private")
async def cmd_db_check(message: Message):
    """Проверить конкретный чат по ID."""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ Укажи ID чата:\n"
            "<code>/db_check -123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        chat_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ Некорректный ID чата.")
        return
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat, Activist
        
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await message.answer(f"❌ Чат с ID <code>{chat_id}</code> не найден в базе.", parse_mode="HTML")
            return
        
        stmt = select(Activist).where(Activist.chat_pk == chat.id)
        result = await session.execute(stmt)
        activists = result.scalars().all()
    
    type_name = "🏋️ Тренерский" if chat.chat_type == "trainer" else "👥 Обычный"
    sheet_status = "✅" if chat.google_sheet_url else "❌"
    
    lines = [
        f"📊 <b>Чат: {chat.title or 'Без названия'}</b>\n",
        f"🆔 ID: <code>{chat.chat_id}</code>",
        f"🏷 Тип: {type_name}",
        f"📊 Таблица: {sheet_status}",
        f"👥 Активистов: <b>{len(activists)}</b>\n",
    ]
    
    if activists:
        lines.append("<b>Список:</b>")
        for i, a in enumerate(activists[:50], 1):
            group_part = f" ({a.group_name})" if a.group_name else ""
            phone_part = f" 📞{a.phone}" if a.phone else ""
            lines.append(f"{i}. {a.full_name} @{a.username}{group_part}{phone_part}")
        
        if len(activists) > 50:
            lines.append(f"\n<i>...и ещё {len(activists) - 50}</i>")
    
    await message.answer("\n".join(lines), parse_mode="HTML")
