from datetime import datetime, timezone, timedelta

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


def get_moscow_now() -> datetime:
    """Получить текущее время по Москве."""
    return datetime.now(MOSCOW_TZ).replace(tzinfo=None)


def to_moscow(dt: datetime) -> datetime:
    """Конвертировать datetime в московское время."""
    if dt.tzinfo is None:
        # Если без таймзоны - считаем что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ).replace(tzinfo=None)

