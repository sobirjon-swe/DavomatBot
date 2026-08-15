import os

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """.env noto'g'ri to'ldirilganda ko'tariladi."""


def _get_str(name: str, default: str = "") -> str:
    return (os.getenv(name) or "").strip() or default


def _get_int(name: str, default: int = 0) -> int:
    raw = _get_str(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(
            f"{name} butun son bo'lishi kerak, berilgan qiymat: {raw!r}. "
            f".env faylni tekshiring."
        ) from None


BOT_TOKEN: str = _get_str("BOT_TOKEN")
DATABASE_URL: str = _get_str("DATABASE_URL")
SUPERADMIN_ID: int = _get_int("SUPERADMIN_ID")
CHANNEL_ID: int = _get_int("CHANNEL_ID")

REDIS_URL: str = _get_str("REDIS_URL")
INITIAL_ACCESS_PASSWORD: str = _get_str("INITIAL_ACCESS_PASSWORD")
LOG_LEVEL: str = _get_str("LOG_LEVEL", "INFO").upper()

# Parolni ketma-ket necha marta xato kiritgach foydalanuvchi bloklanadi
MAX_PASSWORD_ATTEMPTS: int = 3

# Yangi parol uchun eng kam uzunlik
MIN_PASSWORD_LENGTH: int = 6

# Bitta hisobotga biriktiriladigan rasmlar soni
MIN_REPORT_PHOTOS: int = 3
MAX_REPORT_PHOTOS: int = 7

# Hisobotlar sanasi shu vaqt mintaqasi bo'yicha hisoblanadi
TIMEZONE: str = "Asia/Tashkent"


def validate() -> None:
    """Bot ishga tushishidan oldin majburiy sozlamalarni tekshiradi."""
    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", BOT_TOKEN),
            ("DATABASE_URL", DATABASE_URL),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            f".env faylda quyidagilar to'ldirilmagan: {', '.join(missing)}. "
            f"Namuna uchun .env.example ga qarang."
        )

    if not SUPERADMIN_ID:
        raise ConfigError(
            "SUPERADMIN_ID to'ldirilmagan — superadmin ro'yxatdan o'ta olmaydi."
        )

    if not CHANNEL_ID:
        raise ConfigError(
            "CHANNEL_ID to'ldirilmagan. Bu taklif havolasi emas, "
            "-100 bilan boshlanadigan raqam bo'lishi kerak."
        )


DISTRICTS: list[tuple[str, str]] = [
    ("Toshkent shahar", "г. Ташкент"),
    ("Bo'stonliq tumani", "Бустонлыкский район"),
    ("Parkent tumani", "Паркентский район"),
    ("Chirchiq shahar", "г. Чирчик"),
    ("Qibray tumani", "Кибрайский район"),
    ("Toshkent tumani", "Ташкентский район"),
    ("Zangiota tumani", "Зангиатинский район"),
    ("Yangiyo'l shahar", "г. Янгиюль"),
    ("Chinoz tumani", "Чиназский район"),
    ("Nurafshon shahar", "г. Нурафшон"),
    ("O'rtachirchiq tumani", "Уртачирчикский район"),
    ("Quyichirchiq tumani", "Куйичирчикский район"),
    ("Yuqorichirchiq tumani", "Юкоричирчикский район"),
    ("Ohangaron tumani", "Ахангаранский район"),
    ("Ohangaron shahar", "г. Ахангаран"),
    ("Angren shahar", "г. Ангрен"),
    ("Olmaliq shahar", "г. Алмалык"),
    ("Bekobod tumani", "Бекабадский район"),
    ("Bekobod shahar", "г. Бекабад"),
    ("Bo'ka tumani", "Букинский район"),
    ("Oqqo'rg'on tumani", "Аккурганский район"),
    ("Piskent tumani", "Пискентский район"),
]
