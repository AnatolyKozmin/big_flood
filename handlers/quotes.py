import logging

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository, QuoteRepository
from filters import BangCommand
from services.quote_generator import QuoteImageGenerator

logger = logging.getLogger(__name__)

router = Router(name="quotes")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(BangCommand("цитата"))
async def cmd_add_quote(message: Message, session: AsyncSession, command_args: str):
    """!цитата — сохранить цитату и сгенерировать картинку."""
    from database.repositories import QuoteTemplateRepository
    from services.quote_generator import QuoteConfig
    import io
    
    # Логируем для отладки
    logger.info(f"Quote command from {message.from_user.id}, reply_to_message: {message.reply_to_message is not None}")
    
    if not message.reply_to_message:
        await message.answer(
            "❌ Ответь на сообщение, чтобы сохранить его как цитату!\n\n"
            "<i>Нажми на сообщение → Ответить → напиши !цитата</i>",
            parse_mode="HTML"
        )
        return
    
    reply = message.reply_to_message
    quote_text = reply.text or reply.caption
    
    logger.info(f"Reply message: text={bool(reply.text)}, caption={bool(reply.caption)}")
    
    if not quote_text:
        await message.answer("❌ В сообщении нет текста для цитаты!")
        return
    
    chat_repo = ChatRepository(session)
    quote_repo = QuoteRepository(session)
    template_repo = QuoteTemplateRepository(session)
    
    chat = await chat_repo.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title
    )
    
    author_name = None
    author_id = None
    if reply.from_user:
        author_name = reply.from_user.full_name
        author_id = reply.from_user.id
    
    # Сохраняем цитату
    quote = await quote_repo.add(
        chat=chat,
        text=quote_text,
        added_by_id=message.from_user.id,
        added_by_name=message.from_user.full_name,
        author_name=author_name,
        author_id=author_id,
    )
    
    # Генерируем картинку
    try:
        # Получаем шаблон из БД
        template = await template_repo.get_by_chat(chat)
        
        if template:
            config = QuoteConfig.from_template(template)
        else:
            config = QuoteConfig()
        
        generator = QuoteImageGenerator(config)
        
        # Пробуем получить аватарку автора
        avatar_bytes = None
        if author_id and config.avatar_enabled:
            try:
                photos = await message.bot.get_user_profile_photos(author_id, limit=1)
                if photos.photos and photos.photos[0]:
                    photo_file = await message.bot.get_file(photos.photos[0][0].file_id)
                    avatar_bio = io.BytesIO()
                    await message.bot.download_file(photo_file.file_path, avatar_bio)
                    avatar_bytes = avatar_bio.getvalue()
            except Exception as e:
                logger.debug(f"Could not get avatar for user {author_id}: {e}")
        
        image_bytes = generator.generate(
            quote_text=quote_text,
            author_name=author_name,
            quote_id=quote.id,
            avatar_bytes=avatar_bytes,
        )
        
        # Отправляем картинку
        photo = BufferedInputFile(image_bytes, filename=f"quote_{quote.id}.png")
        await message.answer_photo(
            photo,
            caption=f"✅ Цитата #{quote.id} сохранена!"
        )
        
    except Exception as e:
        # Fallback — просто текст если генерация не удалась
        logger.error(f"Quote image generation failed: {e}")
        await message.answer(f"✅ Цитата #{quote.id} сохранена!")


@router.message(BangCommand("мудрость"))
async def cmd_random_quote(message: Message, session: AsyncSession, command_args: str):
    """!мудрость — случайная цитата (с картинкой)."""
    from database.repositories import QuoteTemplateRepository
    from services.quote_generator import QuoteConfig
    
    chat_repo = ChatRepository(session)
    quote_repo = QuoteRepository(session)
    template_repo = QuoteTemplateRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("📭 В этом чате ещё нет цитат. Добавь первую командой !цитата")
        return
    
    quote = await quote_repo.get_random_by_chat(chat)
    if not quote:
        await message.answer("📭 В этом чате ещё нет цитат. Добавь первую командой !цитата")
        return
    
    # Генерируем картинку
    try:
        # Получаем шаблон из БД
        template = await template_repo.get_by_chat(chat)
        
        if template:
            config = QuoteConfig.from_template(template)
        else:
            config = QuoteConfig()
        
        generator = QuoteImageGenerator(config)
        
        # Пробуем получить аватарку автора
        avatar_bytes = None
        if quote.author_id and config.avatar_enabled:
            try:
                photos = await message.bot.get_user_profile_photos(quote.author_id, limit=1)
                if photos.photos and photos.photos[0]:
                    photo_file = await message.bot.get_file(photos.photos[0][0].file_id)
                    import io
                    avatar_bio = io.BytesIO()
                    await message.bot.download_file(photo_file.file_path, avatar_bio)
                    avatar_bytes = avatar_bio.getvalue()
            except Exception as e:
                logger.debug(f"Could not get avatar for user {quote.author_id}: {e}")
        
        image_bytes = generator.generate(
            quote_text=quote.text,
            author_name=quote.author_name,
            quote_id=quote.id,
            avatar_bytes=avatar_bytes,
        )
        
        # Отправляем как фото
        photo = BufferedInputFile(image_bytes, filename=f"quote_{quote.id}.png")
        await message.answer_photo(photo)
        
    except Exception as e:
        # Fallback на текстовый формат если генерация не удалась
        logger.error(f"Quote image generation failed: {e}")
        
        author = f"\n\n— <i>{quote.author_name}</i>" if quote.author_name else ""
        await message.answer(
            f"💬 <b>Мудрость #{quote.id}:</b>\n\n"
            f"«{quote.text}»{author}",
            parse_mode="HTML"
        )
