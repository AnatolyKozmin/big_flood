"""
Сервис для парсинга данных из Google Sheets.

Поддерживает публичные таблицы через CSV export.
Формат таблицы для активистов:
- Колонка A: ФИО (обязательно)
- Колонка B: Username (без @, опционально)
- Колонка C: Роль (опционально)
- Колонка D: Описание/инфо (опционально)
"""

import csv
import io
import logging
import re
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ParsedActivist:
    """
    Распарсенный активист из таблицы.
    
    Формат таблицы:
    ФИО | Юзернейм в тг | Группа | Номер телефона | Есть права | Адрес
    """
    full_name: str  # Обязательно
    username: str  # Обязательно
    surname: Optional[str]  # Извлекается из ФИО
    group_name: Optional[str]  # Группа
    phone: Optional[str]  # Номер телефона
    has_license: Optional[str]  # Есть права
    address: Optional[str]  # Адрес


class GoogleSheetsService:
    """Сервис для работы с Google Sheets."""
    
    # Паттерн для извлечения ID таблицы из URL
    SHEET_ID_PATTERN = re.compile(r'/spreadsheets/d/([a-zA-Z0-9-_]+)')
    
    @classmethod
    def extract_sheet_id(cls, url: str) -> Optional[str]:
        """Извлечь ID таблицы из URL."""
        match = cls.SHEET_ID_PATTERN.search(url)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def get_csv_export_url(cls, sheet_id: str, gid: str = "0") -> str:
        """Получить URL для экспорта таблицы в CSV."""
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    @classmethod
    async def fetch_csv(cls, url: str) -> Optional[str]:
        """Скачать CSV контент по URL."""
        sheet_id = cls.extract_sheet_id(url)
        if not sheet_id:
            logger.error(f"Could not extract sheet ID from URL: {url}")
            return None
        
        csv_url = cls.get_csv_export_url(sheet_id)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(csv_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch CSV: HTTP {response.status}")
                        return None
                    
                    content = await response.text()
                    return content
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching CSV: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching CSV: {e}")
            return None
    
    @classmethod
    def parse_csv_to_activists(cls, csv_content: str) -> list[ParsedActivist]:
        """
        Парсит CSV контент в список активистов.
        
        Ожидаемый формат:
        ФИО | Юзернейм в тг | Группа | Номер телефона | Есть права | Адрес
        """
        activists = []
        
        reader = csv.reader(io.StringIO(csv_content))
        
        # Пропускаем заголовок если есть
        first_row = next(reader, None)
        if first_row is None:
            return activists
        
        # Проверяем, является ли первая строка заголовком
        first_cell = first_row[0].lower().strip() if first_row else ""
        is_header = any(keyword in first_cell for keyword in ["имя", "фио", "name", "фамилия", "участник"])
        
        # Если первая строка не заголовок, обрабатываем её
        if not is_header:
            activist = cls._parse_row(first_row)
            if activist:
                activists.append(activist)
        
        # Обрабатываем остальные строки
        for row in reader:
            activist = cls._parse_row(row)
            if activist:
                activists.append(activist)
        
        return activists
    
    @classmethod
    def _parse_row(cls, row: list[str]) -> Optional[ParsedActivist]:
        """
        Парсит одну строку CSV в активиста.
        
        Формат: ФИО | Юзернейм в тг | Группа | Номер телефона | Есть права | Адрес
        """
        if not row or not row[0].strip():
            return None
        
        # ФИО (обязательно)
        full_name = row[0].strip()
        if not full_name:
            return None
        
        # Юзернейм (обязательно)
        username = row[1].strip().lstrip("@") if len(row) > 1 and row[1].strip() else None
        if not username:
            return None  # Пропускаем строки без юзернейма
        
        # Извлекаем фамилию (последнее слово в ФИО)
        name_parts = full_name.split()
        surname = name_parts[-1] if len(name_parts) > 1 else None
        
        # Группа (колонка C)
        group_name = row[2].strip() if len(row) > 2 and row[2].strip() else None
        
        # Номер телефона (колонка D)
        phone = row[3].strip() if len(row) > 3 and row[3].strip() else None
        
        # Есть права (колонка E)
        has_license = row[4].strip() if len(row) > 4 and row[4].strip() else None
        
        # Адрес (колонка F)
        address = row[5].strip() if len(row) > 5 and row[5].strip() else None
        
        return ParsedActivist(
            full_name=full_name,
            username=username,
            surname=surname,
            group_name=group_name,
            phone=phone,
            has_license=has_license,
            address=address,
        )
    
    @classmethod
    async def fetch_and_parse(cls, url: str) -> tuple[list[ParsedActivist], Optional[str]]:
        """
        Скачивает и парсит таблицу.
        
        Возвращает (список активистов, сообщение об ошибке или None).
        """
        csv_content = await cls.fetch_csv(url)
        
        if csv_content is None:
            return [], "Не удалось скачать таблицу. Убедитесь, что она публичная."
        
        try:
            activists = cls.parse_csv_to_activists(csv_content)
            if not activists:
                return [], "Таблица пуста или имеет неверный формат."
            return activists, None
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            return [], f"Ошибка парсинга: {str(e)}"
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Проверить, что URL похож на Google Sheets."""
        return bool(cls.extract_sheet_id(url))

