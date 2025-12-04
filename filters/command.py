from typing import Optional
from aiogram.filters import BaseFilter
from aiogram.types import Message


class BangCommand(BaseFilter):
    """Фильтр для команд с префиксом '!'."""
    
    def __init__(self, command: str, ignore_case: bool = True):
        self.command = command.lower() if ignore_case else command
        self.ignore_case = ignore_case
    
    async def __call__(self, message: Message) -> bool | dict:
        if not message.text:
            return False
        
        text = message.text.strip()
        if not text.startswith("!"):
            return False
        
        # Убираем ! и разбиваем на части
        parts = text[1:].split(maxsplit=1)
        if not parts:
            return False
        
        cmd = parts[0].lower() if self.ignore_case else parts[0]
        
        if cmd == self.command:
            # Возвращаем аргументы команды
            args = parts[1] if len(parts) > 1 else ""
            return {"command_args": args}
        
        return False

