"""
Генератор изображений для цитат.

Создаёт красивые картинки с текстом цитаты, аватаркой и именем автора.
Поддерживает настраиваемые шаблоны через QuoteTemplate.
"""

import io
import logging
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from database.models import QuoteTemplate

logger = logging.getLogger(__name__)

# Директория с ресурсами (шрифты, шаблоны)
ASSETS_DIR = Path(__file__).parent.parent / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
FONTS_DIR = ASSETS_DIR / "fonts"
AVATARS_DIR = ASSETS_DIR / "avatars"


@dataclass
class QuoteConfig:
    """Конфигурация для генерации цитаты."""
    # Размеры
    image_width: int = 800
    image_height: int = 600
    
    # Фон
    background_path: Optional[str] = None
    background_color: str = "#1e1e28"
    
    # Текст цитаты
    text_x: int = 60
    text_y: int = 100
    text_width: int = 680
    text_height: int = 300
    text_color: str = "#ffffff"
    text_font_size: int = 32
    
    # Аватарка
    avatar_x: int = 350
    avatar_y: int = 420
    avatar_size: int = 80
    avatar_enabled: bool = True
    
    # Автор
    author_x: int = 400
    author_y: int = 520
    author_color: str = "#ffc107"
    author_font_size: int = 24
    
    # Шрифт
    font_path: Optional[str] = None
    
    @classmethod
    def from_template(cls, template: "QuoteTemplate") -> "QuoteConfig":
        """Создать конфиг из модели QuoteTemplate."""
        return cls(
            image_width=template.image_width,
            image_height=template.image_height,
            background_path=template.background_path,
            background_color=template.background_color,
            text_x=template.text_x,
            text_y=template.text_y,
            text_width=template.text_width,
            text_height=template.text_height,
            text_color=template.text_color,
            text_font_size=template.text_font_size,
            avatar_x=template.avatar_x,
            avatar_y=template.avatar_y,
            avatar_size=template.avatar_size,
            avatar_enabled=template.avatar_enabled,
            author_x=template.author_x,
            author_y=template.author_y,
            author_color=template.author_color,
            author_font_size=template.author_font_size,
            font_path=template.font_path,
        )


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Конвертировать HEX цвет в RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def make_circle_avatar(image: Image.Image, size: int) -> Image.Image:
    """Сделать круглую аватарку как в Telegram."""
    # Ресайзим до нужного размера
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    
    # Создаём маску круга
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    # Применяем маску
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(image, (0, 0))
    output.putalpha(mask)
    
    return output


class QuoteImageGenerator:
    """Генератор изображений с цитатами."""
    
    def __init__(self, config: Optional[QuoteConfig] = None):
        self.config = config or QuoteConfig()
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Получить шрифт."""
        # Пробуем кастомный шрифт из конфига
        if self.config.font_path and os.path.exists(self.config.font_path):
            try:
                return ImageFont.truetype(self.config.font_path, size)
            except Exception as e:
                logger.warning(f"Could not load custom font: {e}")
        
        # Пробуем шрифт из папки assets
        for font_name in ["main.ttf", "DejaVuSans.ttf"]:
            font_path = FONTS_DIR / font_name
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception:
                    continue
        
        # Системные шрифты
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
        
        return ImageFont.load_default()
    
    def _load_background(self) -> Image.Image:
        """Загрузить или создать фон."""
        width = self.config.image_width
        height = self.config.image_height
        
        # Пробуем загрузить фоновое изображение
        if self.config.background_path and os.path.exists(self.config.background_path):
            try:
                bg = Image.open(self.config.background_path)
                bg = bg.resize((width, height), Image.Resampling.LANCZOS)
                return bg.convert("RGBA")
            except Exception as e:
                logger.warning(f"Could not load background: {e}")
        
        # Создаём однотонный фон
        bg_color = hex_to_rgb(self.config.background_color)
        return Image.new("RGBA", (width, height), (*bg_color, 255))
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Разбить текст на строки по ширине."""
        # Оценка символов в строке
        try:
            avg_char_width = font.getlength("А")
        except:
            avg_char_width = self.config.text_font_size * 0.6
        
        chars_per_line = int(max_width / avg_char_width) if avg_char_width > 0 else 40
        chars_per_line = max(10, chars_per_line)
        
        return textwrap.wrap(text, width=chars_per_line)
    
    def generate(
        self,
        quote_text: str,
        author_name: Optional[str] = None,
        quote_id: Optional[int] = None,
        avatar_bytes: Optional[bytes] = None,
    ) -> bytes:
        """
        Сгенерировать изображение с цитатой.
        
        Args:
            quote_text: Текст цитаты
            author_name: Имя автора
            quote_id: ID цитаты (для отображения)
            avatar_bytes: Байты аватарки автора
        
        Returns:
            bytes: PNG изображение
        """
        cfg = self.config
        
        # Создаём/загружаем фон
        img = self._load_background()
        draw = ImageDraw.Draw(img)
        
        # Шрифты
        text_font = self._get_font(cfg.text_font_size)
        author_font = self._get_font(cfg.author_font_size)
        
        # Цвета
        text_color = hex_to_rgb(cfg.text_color)
        author_color = hex_to_rgb(cfg.author_color)
        
        # === ТЕКСТ ЦИТАТЫ ===
        lines = self._wrap_text(quote_text, text_font, cfg.text_width)
        line_height = cfg.text_font_size + 8
        
        # Центрируем текст вертикально в области
        total_text_height = len(lines) * line_height
        start_y = cfg.text_y + (cfg.text_height - total_text_height) // 2
        start_y = max(cfg.text_y, start_y)
        
        # Рисуем кавычки
        quote_mark_font = self._get_font(60)
        draw.text((cfg.text_x - 10, start_y - 40), "«", font=quote_mark_font, fill=(*author_color, 100))
        
        # Рисуем строки
        current_y = start_y
        for line in lines:
            # Центрируем по горизонтали в области text_width
            try:
                bbox = draw.textbbox((0, 0), line, font=text_font)
                line_width = bbox[2] - bbox[0]
            except:
                line_width = len(line) * cfg.text_font_size * 0.6
            
            x = cfg.text_x + (cfg.text_width - line_width) // 2
            draw.text((x, current_y), line, font=text_font, fill=text_color)
            current_y += line_height
        
        # Закрывающая кавычка
        draw.text((cfg.text_x + cfg.text_width - 40, current_y - 20), "»", 
                  font=quote_mark_font, fill=(*author_color, 100))
        
        # === АВАТАРКА ===
        if cfg.avatar_enabled and avatar_bytes:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_bytes))
                circle_avatar = make_circle_avatar(avatar_img, cfg.avatar_size)
                
                # Центрируем аватарку по X
                avatar_x = cfg.avatar_x - cfg.avatar_size // 2
                img.paste(circle_avatar, (avatar_x, cfg.avatar_y), circle_avatar)
            except Exception as e:
                logger.warning(f"Could not add avatar: {e}")
        
        # === ИМЯ АВТОРА ===
        if author_name:
            author_text = f"— {author_name}"
            try:
                bbox = draw.textbbox((0, 0), author_text, font=author_font)
                author_width = bbox[2] - bbox[0]
            except:
                author_width = len(author_text) * cfg.author_font_size * 0.6
            
            # Центрируем по X
            author_x = cfg.author_x - author_width // 2
            draw.text((author_x, cfg.author_y), author_text, font=author_font, fill=author_color)
        
        # === НОМЕР ЦИТАТЫ ===
        if quote_id:
            id_font = self._get_font(16)
            id_text = f"#{quote_id}"
            draw.text((cfg.image_width - 60, cfg.image_height - 30), id_text, 
                     font=id_font, fill=(150, 150, 150))
        
        # Сохраняем
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def generate_preview(self, show_zones: bool = True) -> bytes:
        """
        Сгенерировать превью шаблона с красными зонами.
        
        Args:
            show_zones: Показывать красные рамки зон
        
        Returns:
            bytes: PNG изображение
        """
        cfg = self.config
        
        # Создаём фон
        img = self._load_background()
        draw = ImageDraw.Draw(img)
        
        if show_zones:
            # Красный цвет для зон
            zone_color = (255, 0, 0, 180)
            zone_fill = (255, 0, 0, 30)
            
            # Зона текста цитаты
            draw.rectangle(
                [cfg.text_x, cfg.text_y, cfg.text_x + cfg.text_width, cfg.text_y + cfg.text_height],
                outline=zone_color, width=3
            )
            # Подпись
            font = self._get_font(14)
            draw.text((cfg.text_x + 5, cfg.text_y + 5), "ТЕКСТ ЦИТАТЫ", font=font, fill=zone_color)
            
            # Зона аватарки (круг)
            if cfg.avatar_enabled:
                avatar_x = cfg.avatar_x - cfg.avatar_size // 2
                draw.ellipse(
                    [avatar_x, cfg.avatar_y, avatar_x + cfg.avatar_size, cfg.avatar_y + cfg.avatar_size],
                    outline=zone_color, width=3
                )
                draw.text((avatar_x, cfg.avatar_y - 20), "АВАТАР", font=font, fill=zone_color)
            
            # Зона имени автора
            draw.rectangle(
                [cfg.author_x - 100, cfg.author_y, cfg.author_x + 100, cfg.author_y + cfg.author_font_size + 10],
                outline=zone_color, width=2
            )
            draw.text((cfg.author_x - 95, cfg.author_y + 2), "ИМЯ АВТОРА", font=font, fill=zone_color)
            
            # Размеры изображения
            size_text = f"{cfg.image_width}x{cfg.image_height}"
            draw.text((10, cfg.image_height - 25), size_text, font=font, fill=(200, 200, 200))
        
        # Пример текста
        text_font = self._get_font(cfg.text_font_size)
        author_font = self._get_font(cfg.author_font_size)
        
        example_text = "Пример текста цитаты для предпросмотра шаблона"
        text_color = hex_to_rgb(cfg.text_color)
        author_color = hex_to_rgb(cfg.author_color)
        
        # Текст в центре зоны
        try:
            bbox = draw.textbbox((0, 0), example_text, font=text_font)
            tw = bbox[2] - bbox[0]
        except:
            tw = len(example_text) * cfg.text_font_size * 0.5
        
        tx = cfg.text_x + (cfg.text_width - tw) // 2
        ty = cfg.text_y + cfg.text_height // 2 - cfg.text_font_size // 2
        draw.text((tx, ty), example_text, font=text_font, fill=(*text_color, 150))
        
        # Пример автора
        author_text = "— Имя Автора"
        try:
            bbox = draw.textbbox((0, 0), author_text, font=author_font)
            aw = bbox[2] - bbox[0]
        except:
            aw = len(author_text) * cfg.author_font_size * 0.5
        
        ax = cfg.author_x - aw // 2
        draw.text((ax, cfg.author_y), author_text, font=author_font, fill=(*author_color, 150))
        
        # Пример аватарки (серый круг)
        if cfg.avatar_enabled:
            avatar_x = cfg.avatar_x - cfg.avatar_size // 2
            draw.ellipse(
                [avatar_x + 5, cfg.avatar_y + 5, 
                 avatar_x + cfg.avatar_size - 5, cfg.avatar_y + cfg.avatar_size - 5],
                fill=(100, 100, 100, 150)
            )
        
        # Сохраняем
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        
        return buffer.getvalue()


# Создаём директории для ресурсов
def ensure_assets_dirs():
    """Создать директории для ресурсов."""
    ASSETS_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)
    FONTS_DIR.mkdir(exist_ok=True)
    AVATARS_DIR.mkdir(exist_ok=True)


ensure_assets_dirs()
