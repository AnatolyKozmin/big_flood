from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ChatRepository, QuoteRepository
from filters import BangCommand

router = Router(name="quotes")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(BangCommand("цитата"))
async def cmd_add_quote(message: Message, session: AsyncSession, command_args: str):
    """!цитата — сохранить цитату (в ответ на сообщение)."""
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение, чтобы сохранить его как цитату!")
        return
    
    reply = message.reply_to_message
    quote_text = reply.text or reply.caption
    
    if not quote_text:
        await message.answer("❌ В сообщении нет текста для цитаты!")
        return
    
    chat_repo = ChatRepository(session)
    quote_repo = QuoteRepository(session)
    
    chat = await chat_repo.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title
    )
    
    author_name = None
    author_id = None
    if reply.from_user:
        author_name = reply.from_user.full_name
        author_id = reply.from_user.id
    
    quote = await quote_repo.add(
        chat=chat,
        text=quote_text,
        added_by_id=message.from_user.id,
        added_by_name=message.from_user.full_name,
        author_name=author_name,
        author_id=author_id,
    )
    
    await message.answer(f"✅ Цитата #{quote.id} сохранена!")


@router.message(BangCommand("мудрость"))
async def cmd_random_quote(message: Message, session: AsyncSession, command_args: str):
    """!мудрость — случайная цитата."""
    chat_repo = ChatRepository(session)
    quote_repo = QuoteRepository(session)
    
    chat = await chat_repo.get_by_chat_id(message.chat.id)
    if not chat:
        await message.answer("📭 В этом чате ещё нет цитат. Добавь первую командой !цитата")
        return
    
    quote = await quote_repo.get_random_by_chat(chat)
    if not quote:
        await message.answer("📭 В этом чате ещё нет цитат. Добавь первую командой !цитата")
        return
    
    author = f"\n\n— <i>{quote.author_name}</i>" if quote.author_name else ""
    
    await message.answer(
        f"💬 <b>Мудрость #{quote.id}:</b>\n\n"
        f"«{quote.text}»{author}",
        parse_mode="HTML"
    )
