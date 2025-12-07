"""
Генератор изображений для цитат.

Создаёт красивые картинки с текстом цитаты.
"""

import io
import logging
import os
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Директория с ресурсами (шрифты, шаблоны)
ASSETS_DIR = Path(__file__).parent.parent / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
FONTS_DIR = ASSETS_DIR / "fonts"

# Дефолтные настройки
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
DEFAULT_BG_COLOR = (30, 30, 40)  # Тёмно-серый
DEFAULT_TEXT_COLOR = (255, 255, 255)  # Белый
DEFAULT_ACCENT_COLOR = (255, 193, 7)  # Золотой
DEFAULT_FONT_SIZE = 32
AUTHOR_FONT_SIZE = 24


class QuoteImageGenerator:
    """Генератор изображений с цитатами."""
    
    def __init__(
        self,
        template_path: Optional[str] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        self.template_path = template_path
        self.width = width
        self.height = height
        self._font = None
        self._font_italic = None
    
    def _get_font(self, size: int, italic: bool = False) -> ImageFont.FreeTypeFont:
        """Получить шрифт. Пытается загрузить кастомный, иначе использует дефолтный."""
        font_name = "DejaVuSans-Oblique.ttf" if italic else "DejaVuSans.ttf"
        
        # Пробуем кастомный шрифт
        custom_font_path = FONTS_DIR / font_name
        if custom_font_path.exists():
            try:
                return ImageFont.truetype(str(custom_font_path), size)
            except Exception as e:
                logger.warning(f"Could not load custom font: {e}")
        
        # Пробуем системные шрифты
        system_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        
        for font_path in system_fonts:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
        
        # Fallback на встроенный шрифт
        return ImageFont.load_default()
    
    def _load_template(self) -> Optional[Image.Image]:
        """Загрузить шаблон (плашку) если есть."""
        if not self.template_path:
            return None
        
        try:
            # Проверяем путь
            if os.path.exists(self.template_path):
                template = Image.open(self.template_path)
                return template.convert("RGBA")
        except Exception as e:
            logger.warning(f"Could not load template: {e}")
        
        return None
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Разбить текст на строки по ширине."""
        # Оценка символов в строке
        avg_char_width = font.getlength("А")
        chars_per_line = int(max_width / avg_char_width) if avg_char_width > 0 else 40
        
        # Разбиваем текст
        wrapped = textwrap.wrap(text, width=chars_per_line)
        return wrapped
    
    def generate(
        self,
        quote_text: str,
        author_name: Optional[str] = None,
        quote_id: Optional[int] = None,
    ) -> bytes:
        """
        Сгенерировать изображение с цитатой.
        
        Returns:
            bytes: PNG изображение в байтах
        """
        # Загружаем шаблон или создаём фон
        template = self._load_template()
        
        if template:
            img = template.resize((self.width, self.height), Image.Resampling.LANCZOS)
        else:
            img = self._create_gradient_background()
        
        draw = ImageDraw.Draw(img)
        
        # Получаем шрифты
        quote_font = self._get_font(DEFAULT_FONT_SIZE)
        author_font = self._get_font(AUTHOR_FONT_SIZE, italic=True)
        
        # Отступы
        padding = 60
        max_text_width = self.width - (padding * 2)
        
        # Разбиваем текст на строки
        quote_lines = self._wrap_text(quote_text, quote_font, max_text_width)
        
        # Вычисляем высоту текста
        line_height = DEFAULT_FONT_SIZE + 10
        total_quote_height = len(quote_lines) * line_height
        
        # Добавляем автора
        author_text = f"— {author_name}" if author_name else None
        author_height = AUTHOR_FONT_SIZE + 20 if author_text else 0
        
        # Номер цитаты
        id_text = f"#{quote_id}" if quote_id else None
        id_height = 30 if id_text else 0
        
        total_height = total_quote_height + author_height + id_height + 40
        
        # Начальная позиция Y (центрируем)
        start_y = (self.height - total_height) // 2
        
        # Рисуем кавычки
        self._draw_quote_marks(draw, padding, start_y - 20)
        
        # Рисуем текст цитаты
        current_y = start_y
        for line in quote_lines:
            # Центрируем каждую строку
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), line, font=quote_font, fill=DEFAULT_TEXT_COLOR)
            current_y += line_height
        
        # Рисуем автора
        if author_text:
            current_y += 20
            bbox = draw.textbbox((0, 0), author_text, font=author_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), author_text, font=author_font, fill=DEFAULT_ACCENT_COLOR)
            current_y += AUTHOR_FONT_SIZE + 10
        
        # Рисуем номер цитаты
        if id_text:
            current_y += 10
            id_font = self._get_font(18)
            draw.text((self.width - padding - 50, self.height - 40), id_text, 
                     font=id_font, fill=(150, 150, 150))
        
        # Сохраняем в байты
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def _create_gradient_background(self) -> Image.Image:
        """Создать градиентный фон."""
        img = Image.new("RGBA", (self.width, self.height))
        
        # Градиент от тёмно-синего к тёмно-фиолетовому
        for y in range(self.height):
            ratio = y / self.height
            r = int(20 + (40 - 20) * ratio)
            g = int(20 + (25 - 20) * ratio)
            b = int(40 + (60 - 40) * ratio)
            
            for x in range(self.width):
                img.putpixel((x, y), (r, g, b, 255))
        
        return img
    
    def _draw_quote_marks(self, draw: ImageDraw.Draw, x: int, y: int):
        """Нарисовать декоративные кавычки."""
        quote_mark_font = self._get_font(80)
        draw.text((x, y), "«", font=quote_mark_font, fill=(255, 193, 7, 100))
        draw.text((self.width - x - 60, y), "»", font=quote_mark_font, fill=(255, 193, 7, 100))


# Создаём директории для ассетов если не существуют
def ensure_assets_dirs():
    """Создать директории для ресурсов."""
    ASSETS_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)
    FONTS_DIR.mkdir(exist_ok=True)


# Вызываем при импорте
ensure_assets_dirs()

