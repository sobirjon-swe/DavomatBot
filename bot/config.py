import os
from datetime import time

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

# ─── Mini App API ───────────────────────────────────────────────────────────

API_HOST: str = _get_str("API_HOST", "127.0.0.1")
API_PORT: int = _get_int("API_PORT", 8000)

def _webapp_url(name: str) -> str:
    """Mini App manzili. Telegram faqat HTTPS ni ochadi."""
    url = _get_str(name)
    if url and not url.startswith("https://"):
        raise ConfigError(
            f"{name} https:// bilan boshlanishi kerak — Telegram Mini App "
            f"shifrlanmagan manzilni ochmaydi. Berilgan qiymat: {url!r}"
        )
    return url.rstrip("/")


# Mini App ochiladigan HTTPS manzil (BotFather ga ham shu kiritiladi).
# Bo'sh qoldirilsa bot Mini App tugmalarini umuman ko'rsatmaydi.
WEBAPP_URL: str = _webapp_url("WEBAPP_URL")

# Brauzerdan kelgan initData qancha vaqt haqiqiy hisoblanadi.
# Telegram uni ilova ochilganda yangilaydi; eski qiymatni qayta ishlatishning
# oldini olish uchun oraliq qisqa tutiladi.
INITDATA_TTL_SECONDS: int = _get_int("INITDATA_TTL_SECONDS", 3600)

# Mini App yuklagan rasmlar avval shu yopiq chatga yuboriladi — Telegram
# file_id qaytaradi va kanalga chiqarish mantig'i o'zgarishsiz qoladi.
STORAGE_CHAT_ID: int = _get_int("STORAGE_CHAT_ID")

# Faqat lokal ishlab chiqish uchun. Mini App Telegram ichida ochilgani uchun
# prodda bo'sh qoldirilsa ham ishlayveradi.
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in _get_str("CORS_ORIGINS").split(",") if origin.strip()
]

# Bitta rasm uchun eng katta hajm (Telegram cheklovi 10 MB)
MAX_PHOTO_BYTES: int = 10 * 1024 * 1024
ALLOWED_PHOTO_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

# Parolni ketma-ket necha marta xato kiritgach foydalanuvchi bloklanadi
MAX_PASSWORD_ATTEMPTS: int = 3

# Yangi parol uchun eng kam uzunlik
MIN_PASSWORD_LENGTH: int = 6

# Bitta hisobotga biriktiriladigan rasmlar soni
MIN_REPORT_PHOTOS: int = 3
MAX_REPORT_PHOTOS: int = 7

# Hisobotlar sanasi shu vaqt mintaqasi bo'yicha hisoblanadi
TIMEZONE: str = "Asia/Tashkent"


# ─── Kunlik eslatmalar ──────────────────────────────────────────────────────

def _get_time(name: str) -> time | None:
    """HH:MM ko'rinishidagi vaqt. Bo'sh bo'lsa vazifa o'chiriladi."""
    raw = _get_str(name)
    if not raw:
        return None
    try:
        hour, minute = raw.split(":")
        return time(int(hour), int(minute))
    except ValueError:
        raise ConfigError(
            f"{name} HH:MM ko'rinishida bo'lishi kerak (masalan 17:00), "
            f"berilgan qiymat: {raw!r}"
        ) from None


def _get_weekdays(name: str, default: str) -> frozenset[int]:
    """Hafta kunlari: 1 = dushanba ... 7 = yakshanba."""
    raw = _get_str(name, default)
    try:
        days = {int(part) for part in raw.split(",") if part.strip()}
    except ValueError:
        raise ConfigError(f"{name} vergul bilan ajratilgan raqamlar bo'lishi kerak") from None

    if not days or not days <= set(range(1, 8)):
        raise ConfigError(f"{name} 1 dan 7 gacha bo'lgan raqamlardan iborat bo'lishi kerak")
    return frozenset(days)


# Hodimga "bugun hisobot bermadingiz" eslatmasi yuboriladigan vaqt
REMINDER_TIME: time | None = _get_time("REMINDER_TIME")

# Adminlarga kunlik yakun (kim hisobot bermadi) yuboriladigan vaqt
SUMMARY_TIME: time | None = _get_time("SUMMARY_TIME")

# Ish kunlari — dam olish kunlari eslatma yuborilmaydi
REMINDER_WEEKDAYS: frozenset[int] = _get_weekdays("REMINDER_WEEKDAYS", "1,2,3,4,5")


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
