"""
Админка для настройки шаблонов цитат.

Позволяет настраивать:
- Размеры картинки
- Расположение текста, аватарки, имени автора
- Цвета и размеры шрифтов
- Фоновое изображение
- Кастомный шрифт
"""

import logging
import os

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.engine import async_session
from database.repositories import ChatRepository, QuoteTemplateRepository
from database.models import QuoteTemplate
from services.quote_generator import QuoteImageGenerator, QuoteConfig

logger = logging.getLogger(__name__)

router = Router(name="quote_admin")


class QuoteTemplateStates(StatesGroup):
    """Состояния для настройки шаблона цитат."""
    waiting_background = State()
    waiting_font = State()
    waiting_value = State()  # Для числовых значений


# ============================================
# КЛАВИАТУРЫ
# ============================================

def build_template_menu_keyboard(chat_pk: int):
    """Главное меню настройки шаблона."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📐 Размеры картинки", callback_data=f"qtpl:size:{chat_pk}")
    builder.button(text="📝 Область текста", callback_data=f"qtpl:text:{chat_pk}")
    builder.button(text="👤 Аватарка", callback_data=f"qtpl:avatar:{chat_pk}")
    builder.button(text="✍️ Имя автора", callback_data=f"qtpl:author:{chat_pk}")
    builder.button(text="🖼 Фон", callback_data=f"qtpl:bg:{chat_pk}")
    builder.button(text="🔤 Шрифт", callback_data=f"qtpl:font:{chat_pk}")
    builder.button(text="👁 Превью с зонами", callback_data=f"qtpl:preview:{chat_pk}")
    builder.button(text="👁 Превью без зон", callback_data=f"qtpl:preview_clean:{chat_pk}")
    builder.button(text="🔄 Сбросить настройки", callback_data=f"qtpl:reset:{chat_pk}")
    builder.button(text="◀️ Назад к чату", callback_data=f"chat:view:{chat_pk}")
    
    builder.adjust(2, 2, 2, 2, 1, 1)
    return builder.as_markup()


def build_size_keyboard(chat_pk: int):
    """Меню настройки размеров."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="800x600 (стандарт)", callback_data=f"qtpl:setsize:{chat_pk}:800:600")
    builder.button(text="1024x768", callback_data=f"qtpl:setsize:{chat_pk}:1024:768")
    builder.button(text="1080x1080 (квадрат)", callback_data=f"qtpl:setsize:{chat_pk}:1080:1080")
    builder.button(text="1200x630 (соцсети)", callback_data=f"qtpl:setsize:{chat_pk}:1200:630")
    builder.button(text="✏️ Своё значение", callback_data=f"qtpl:customsize:{chat_pk}")
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def build_text_keyboard(chat_pk: int, template: QuoteTemplate):
    """Меню настройки области текста."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=f"X: {template.text_x} ▶️", callback_data=f"qtpl:set:{chat_pk}:text_x")
    builder.button(text=f"Y: {template.text_y} ▶️", callback_data=f"qtpl:set:{chat_pk}:text_y")
    builder.button(text=f"Ширина: {template.text_width} ▶️", callback_data=f"qtpl:set:{chat_pk}:text_width")
    builder.button(text=f"Высота: {template.text_height} ▶️", callback_data=f"qtpl:set:{chat_pk}:text_height")
    builder.button(text=f"Размер шрифта: {template.text_font_size} ▶️", callback_data=f"qtpl:set:{chat_pk}:text_font_size")
    builder.button(text=f"Цвет: {template.text_color} ▶️", callback_data=f"qtpl:set:{chat_pk}:text_color")
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def build_avatar_keyboard(chat_pk: int, template: QuoteTemplate):
    """Меню настройки аватарки."""
    builder = InlineKeyboardBuilder()
    
    status = "✅ Вкл" if template.avatar_enabled else "❌ Выкл"
    builder.button(text=f"Аватарка: {status}", callback_data=f"qtpl:toggle_avatar:{chat_pk}")
    builder.button(text=f"X: {template.avatar_x} ▶️", callback_data=f"qtpl:set:{chat_pk}:avatar_x")
    builder.button(text=f"Y: {template.avatar_y} ▶️", callback_data=f"qtpl:set:{chat_pk}:avatar_y")
    builder.button(text=f"Размер: {template.avatar_size} ▶️", callback_data=f"qtpl:set:{chat_pk}:avatar_size")
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def build_author_keyboard(chat_pk: int, template: QuoteTemplate):
    """Меню настройки имени автора."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=f"X: {template.author_x} ▶️", callback_data=f"qtpl:set:{chat_pk}:author_x")
    builder.button(text=f"Y: {template.author_y} ▶️", callback_data=f"qtpl:set:{chat_pk}:author_y")
    builder.button(text=f"Размер шрифта: {template.author_font_size} ▶️", callback_data=f"qtpl:set:{chat_pk}:author_font_size")
    builder.button(text=f"Цвет: {template.author_color} ▶️", callback_data=f"qtpl:set:{chat_pk}:author_color")
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def build_back_keyboard(chat_pk: int):
    """Кнопка назад."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    return builder.as_markup()


# ============================================
# ОСНОВНОЕ МЕНЮ ШАБЛОНА
# ============================================

@router.callback_query(F.data.startswith("qtpl:menu:"))
async def cb_template_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню настройки шаблона цитат."""
    chat_pk = int(callback.data.split(":")[2])
    if state:
        await state.clear()
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await callback.answer("❌ Чат не найден", show_alert=True)
            return
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
    
    text = (
        f"🎨 <b>Настройка шаблона цитат</b>\n\n"
        f"📝 Чат: {chat.title or 'Без названия'}\n\n"
        f"<b>Текущие настройки:</b>\n"
        f"📐 Размер: {template.image_width}x{template.image_height}\n"
        f"📝 Текст: ({template.text_x}, {template.text_y}) {template.text_width}x{template.text_height}\n"
        f"👤 Аватар: {'✅' if template.avatar_enabled else '❌'} ({template.avatar_x}, {template.avatar_y}) {template.avatar_size}px\n"
        f"✍️ Автор: ({template.author_x}, {template.author_y})\n"
        f"🖼 Фон: {'✅ Загружен' if template.background_path else '❌ Нет'}\n"
        f"🔤 Шрифт: {'✅ Загружен' if template.font_path else '🔤 Стандартный'}"
    )
    
    # Если сообщение — фото (после превью), отправляем новое сообщение
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=build_template_menu_keyboard(chat_pk)
        )
    else:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=build_template_menu_keyboard(chat_pk)
        )
    await callback.answer()


# ============================================
# НАСТРОЙКА РАЗМЕРОВ
# ============================================

@router.callback_query(F.data.startswith("qtpl:size:"))
async def cb_template_size(callback: CallbackQuery):
    """Меню размеров картинки."""
    chat_pk = int(callback.data.split(":")[2])
    
    await callback.message.edit_text(
        "📐 <b>Размеры картинки</b>\n\n"
        "Выбери размер или введи свой:",
        parse_mode="HTML",
        reply_markup=build_size_keyboard(chat_pk)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qtpl:setsize:"))
async def cb_set_size(callback: CallbackQuery):
    """Установить размер картинки."""
    parts = callback.data.split(":")
    chat_pk = int(parts[2])
    width = int(parts[3])
    height = int(parts[4])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            await callback.answer("❌ Чат не найден", show_alert=True)
            return
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        await template_repo.update(template, image_width=width, image_height=height)
    
    await callback.answer(f"✅ Размер: {width}x{height}", show_alert=True)
    await cb_template_menu(callback, None)


@router.callback_query(F.data.startswith("qtpl:customsize:"))
async def cb_custom_size(callback: CallbackQuery, state: FSMContext):
    """Ввод кастомного размера."""
    chat_pk = int(callback.data.split(":")[2])
    
    await state.set_state(QuoteTemplateStates.waiting_value)
    await state.update_data(chat_pk=chat_pk, field="custom_size")
    
    await callback.message.edit_text(
        "📐 Введи размер в формате <code>ширина высота</code>\n\n"
        "Пример: <code>900 500</code>\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(chat_pk)
    )
    await callback.answer()


# ============================================
# НАСТРОЙКА ТЕКСТА
# ============================================

@router.callback_query(F.data.startswith("qtpl:text:"))
async def cb_template_text(callback: CallbackQuery):
    """Меню настройки текста."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
    
    await callback.message.edit_text(
        "📝 <b>Настройка области текста</b>\n\n"
        "Текст цитаты будет отображаться в прямоугольной области.\n"
        "X, Y — координаты верхнего левого угла.",
        parse_mode="HTML",
        reply_markup=build_text_keyboard(chat_pk, template)
    )
    await callback.answer()


# ============================================
# НАСТРОЙКА АВАТАРКИ
# ============================================

@router.callback_query(F.data.startswith("qtpl:avatar:"))
async def cb_template_avatar(callback: CallbackQuery):
    """Меню настройки аватарки."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
    
    await callback.message.edit_text(
        "👤 <b>Настройка аватарки</b>\n\n"
        "Аватарка автора цитаты (круглая, как в Telegram).\n"
        "X, Y — координаты центра круга.",
        parse_mode="HTML",
        reply_markup=build_avatar_keyboard(chat_pk, template)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qtpl:toggle_avatar:"))
async def cb_toggle_avatar(callback: CallbackQuery):
    """Включить/выключить аватарку."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        new_value = not template.avatar_enabled
        await template_repo.update(template, avatar_enabled=new_value)
    
    status = "включена" if new_value else "выключена"
    await callback.answer(f"Аватарка {status}", show_alert=True)
    await cb_template_avatar(callback)


# ============================================
# НАСТРОЙКА АВТОРА
# ============================================

@router.callback_query(F.data.startswith("qtpl:author:"))
async def cb_template_author(callback: CallbackQuery):
    """Меню настройки имени автора."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
    
    await callback.message.edit_text(
        "✍️ <b>Настройка имени автора</b>\n\n"
        "Имя автора отображается под цитатой.\n"
        "X, Y — координаты центра текста.",
        parse_mode="HTML",
        reply_markup=build_author_keyboard(chat_pk, template)
    )
    await callback.answer()


# ============================================
# ВВОД ЗНАЧЕНИЯ
# ============================================

@router.callback_query(F.data.startswith("qtpl:set:"))
async def cb_set_value(callback: CallbackQuery, state: FSMContext):
    """Начать ввод значения."""
    parts = callback.data.split(":")
    chat_pk = int(parts[2])
    field = parts[3]
    
    # Человекочитаемые названия
    field_names = {
        "text_x": "X текста",
        "text_y": "Y текста",
        "text_width": "Ширина текста",
        "text_height": "Высота текста",
        "text_font_size": "Размер шрифта текста",
        "text_color": "Цвет текста (HEX)",
        "avatar_x": "X аватарки",
        "avatar_y": "Y аватарки",
        "avatar_size": "Размер аватарки",
        "author_x": "X автора",
        "author_y": "Y автора",
        "author_font_size": "Размер шрифта автора",
        "author_color": "Цвет автора (HEX)",
        "background_color": "Цвет фона (HEX)",
    }
    
    field_name = field_names.get(field, field)
    is_color = "color" in field.lower()
    
    await state.set_state(QuoteTemplateStates.waiting_value)
    await state.update_data(chat_pk=chat_pk, field=field)
    
    example = "#ffffff" if is_color else "100"
    
    await callback.message.edit_text(
        f"✏️ <b>Введи значение для: {field_name}</b>\n\n"
        f"Пример: <code>{example}</code>\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(chat_pk)
    )
    await callback.answer()


@router.message(QuoteTemplateStates.waiting_value, F.chat.type == "private")
async def process_value(message: Message, state: FSMContext):
    """Обработка введённого значения."""
    data = await state.get_data()
    chat_pk = data.get("chat_pk")
    field = data.get("field")
    
    value = message.text.strip()
    
    # Обработка кастомного размера
    if field == "custom_size":
        try:
            parts = value.split()
            width = int(parts[0])
            height = int(parts[1])
            
            if width < 100 or width > 4000 or height < 100 or height > 4000:
                await message.answer("❌ Размер должен быть от 100 до 4000 пикселей.")
                return
            
            async with async_session() as session:
                from sqlalchemy import select
                from database.models import Chat
                
                stmt = select(Chat).where(Chat.id == chat_pk)
                result = await session.execute(stmt)
                chat = result.scalar_one_or_none()
                
                template_repo = QuoteTemplateRepository(session)
                template = await template_repo.get_or_create(chat)
                await template_repo.update(template, image_width=width, image_height=height)
            
            await state.clear()
            await message.answer(
                f"✅ Размер установлен: {width}x{height}",
                reply_markup=build_back_keyboard(chat_pk)
            )
            return
            
        except (ValueError, IndexError):
            await message.answer("❌ Неверный формат. Введи: <code>ширина высота</code>", parse_mode="HTML")
            return
    
    # Обработка цветов
    if "color" in field:
        if not value.startswith("#"):
            value = f"#{value}"
        if len(value) != 7:
            await message.answer("❌ Цвет должен быть в формате HEX: #ffffff")
            return
    else:
        # Числовые значения
        try:
            value = int(value)
            if value < 0 or value > 4000:
                await message.answer("❌ Значение должно быть от 0 до 4000.")
                return
        except ValueError:
            await message.answer("❌ Введи число.")
            return
    
    # Сохраняем
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        await template_repo.update(template, **{field: value})
    
    await state.clear()
    await message.answer(
        f"✅ Значение сохранено!",
        reply_markup=build_back_keyboard(chat_pk)
    )


# ============================================
# ФОН И ШРИФТ
# ============================================

@router.callback_query(F.data.startswith("qtpl:bg:"))
async def cb_template_bg(callback: CallbackQuery, state: FSMContext):
    """Меню настройки фона."""
    chat_pk = int(callback.data.split(":")[2])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Загрузить изображение", callback_data=f"qtpl:upload_bg:{chat_pk}")
    builder.button(text="🎨 Цвет фона", callback_data=f"qtpl:set:{chat_pk}:background_color")
    builder.button(text="🗑 Удалить фон", callback_data=f"qtpl:remove_bg:{chat_pk}")
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    builder.adjust(1, 1, 1, 1)
    
    await callback.message.edit_text(
        "🖼 <b>Настройка фона</b>\n\n"
        "Загрузи изображение или выбери цвет фона.\n"
        "Рекомендуемый размер: соответствует размеру картинки.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qtpl:upload_bg:"))
async def cb_upload_bg(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку фона."""
    chat_pk = int(callback.data.split(":")[2])
    
    await state.set_state(QuoteTemplateStates.waiting_background)
    await state.update_data(chat_pk=chat_pk)
    
    await callback.message.edit_text(
        "🖼 <b>Загрузка фона</b>\n\n"
        "Отправь изображение для фона.\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(chat_pk)
    )
    await callback.answer()


@router.message(QuoteTemplateStates.waiting_background, F.photo, F.chat.type == "private")
async def process_background(message: Message, state: FSMContext, bot: Bot):
    """Обработка загруженного фона."""
    data = await state.get_data()
    chat_pk = data.get("chat_pk")
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    os.makedirs("assets/templates", exist_ok=True)
    file_path = f"assets/templates/bg_{chat_pk}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        await template_repo.update(template, background_path=file_path)
    
    await state.clear()
    await message.answer(
        "✅ Фон загружен!",
        reply_markup=build_back_keyboard(chat_pk)
    )


@router.callback_query(F.data.startswith("qtpl:remove_bg:"))
async def cb_remove_bg(callback: CallbackQuery):
    """Удалить фон."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        
        if template.background_path and os.path.exists(template.background_path):
            os.remove(template.background_path)
        
        await template_repo.update(template, background_path=None)
    
    await callback.answer("✅ Фон удалён", show_alert=True)
    await cb_template_bg(callback, None)


@router.callback_query(F.data.startswith("qtpl:font:"))
async def cb_template_font(callback: CallbackQuery, state: FSMContext):
    """Меню настройки шрифта."""
    chat_pk = int(callback.data.split(":")[2])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Загрузить шрифт (.ttf)", callback_data=f"qtpl:upload_font:{chat_pk}")
    builder.button(text="🗑 Сбросить на стандартный", callback_data=f"qtpl:remove_font:{chat_pk}")
    builder.button(text="◀️ Назад", callback_data=f"qtpl:menu:{chat_pk}")
    builder.adjust(1, 1, 1)
    
    await callback.message.edit_text(
        "🔤 <b>Настройка шрифта</b>\n\n"
        "Загрузи файл шрифта (.ttf) или используй стандартный.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qtpl:upload_font:"))
async def cb_upload_font(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку шрифта."""
    chat_pk = int(callback.data.split(":")[2])
    
    await state.set_state(QuoteTemplateStates.waiting_font)
    await state.update_data(chat_pk=chat_pk)
    
    await callback.message.edit_text(
        "🔤 <b>Загрузка шрифта</b>\n\n"
        "Отправь файл шрифта (.ttf)\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
        reply_markup=build_back_keyboard(chat_pk)
    )
    await callback.answer()


@router.message(QuoteTemplateStates.waiting_font, F.document, F.chat.type == "private")
async def process_font(message: Message, state: FSMContext, bot: Bot):
    """Обработка загруженного шрифта."""
    data = await state.get_data()
    chat_pk = data.get("chat_pk")
    
    doc = message.document
    if not doc.file_name.lower().endswith(".ttf"):
        await message.answer("❌ Нужен файл с расширением .ttf")
        return
    
    file = await bot.get_file(doc.file_id)
    
    os.makedirs("assets/fonts", exist_ok=True)
    file_path = f"assets/fonts/font_{chat_pk}.ttf"
    await bot.download_file(file.file_path, file_path)
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        await template_repo.update(template, font_path=file_path)
    
    await state.clear()
    await message.answer(
        "✅ Шрифт загружен!",
        reply_markup=build_back_keyboard(chat_pk)
    )


@router.callback_query(F.data.startswith("qtpl:remove_font:"))
async def cb_remove_font(callback: CallbackQuery):
    """Удалить шрифт."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
        
        if template.font_path and os.path.exists(template.font_path):
            os.remove(template.font_path)
        
        await template_repo.update(template, font_path=None)
    
    await callback.answer("✅ Шрифт сброшен", show_alert=True)
    await cb_template_font(callback, None)


# ============================================
# ПРЕВЬЮ
# ============================================

@router.callback_query(F.data.startswith("qtpl:preview:"))
async def cb_preview_with_zones(callback: CallbackQuery):
    """Превью с красными зонами."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
    
    config = QuoteConfig.from_template(template)
    generator = QuoteImageGenerator(config)
    
    image_bytes = generator.generate_preview(show_zones=True)
    photo = BufferedInputFile(image_bytes, filename="preview.png")
    
    # Удаляем старое сообщение и отправляем фото
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer_photo(
        photo,
        caption="🔴 Превью с зонами\n\n"
                "Красные рамки показывают области для текста, аватарки и имени.",
        reply_markup=build_back_keyboard(chat_pk)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qtpl:preview_clean:"))
async def cb_preview_clean(callback: CallbackQuery):
    """Превью без зон."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_or_create(chat)
    
    config = QuoteConfig.from_template(template)
    generator = QuoteImageGenerator(config)
    
    image_bytes = generator.generate(
        quote_text="Пример текста цитаты для проверки шаблона",
        author_name="Имя Автора",
        quote_id=42
    )
    photo = BufferedInputFile(image_bytes, filename="preview.png")
    
    # Удаляем старое сообщение и отправляем фото
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer_photo(
        photo,
        caption="👁 Превью цитаты (без зон)",
        reply_markup=build_back_keyboard(chat_pk)
    )
    await callback.answer()


# ============================================
# СБРОС НАСТРОЕК
# ============================================

@router.callback_query(F.data.startswith("qtpl:reset:"))
async def cb_reset_confirm(callback: CallbackQuery):
    """Подтверждение сброса."""
    chat_pk = int(callback.data.split(":")[2])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сбросить", callback_data=f"qtpl:do_reset:{chat_pk}")
    builder.button(text="❌ Отмена", callback_data=f"qtpl:menu:{chat_pk}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "⚠️ <b>Подтверждение</b>\n\n"
        "Сбросить все настройки шаблона на стандартные?",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qtpl:do_reset:"))
async def cb_do_reset(callback: CallbackQuery):
    """Выполнить сброс."""
    chat_pk = int(callback.data.split(":")[2])
    
    async with async_session() as session:
        from sqlalchemy import select
        from database.models import Chat
        
        stmt = select(Chat).where(Chat.id == chat_pk)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        template_repo = QuoteTemplateRepository(session)
        template = await template_repo.get_by_chat(chat)
        
        if template:
            # Удаляем файлы
            if template.background_path and os.path.exists(template.background_path):
                os.remove(template.background_path)
            if template.font_path and os.path.exists(template.font_path):
                os.remove(template.font_path)
            
            await template_repo.delete(template)
    
    await callback.answer("✅ Настройки сброшены", show_alert=True)
    await cb_template_menu(callback, None)

