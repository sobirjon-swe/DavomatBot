from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonCommands,
    MenuButtonWebApp,
    WebAppInfo,
)

import config
from locales import t


def is_enabled() -> bool:
    """WEBAPP_URL sozlanmagan bo'lsa Mini App tugmalari ko'rsatilmaydi."""
    return bool(config.WEBAPP_URL)


def _info() -> WebAppInfo:
    return WebAppInfo(url=config.WEBAPP_URL)


def reply_button(lang: str) -> KeyboardButton | None:
    """Asosiy menyudagi tugma. WebApp tugmalari faqat shaxsiy chatda ishlaydi."""
    if not is_enabled():
        return None
    return KeyboardButton(text=t(lang, "btn_open_app"), web_app=_info())


def inline_kb(lang: str) -> InlineKeyboardMarkup | None:
    """Xabar ostiga qo'yiladigan "ilovani ochish" tugmasi."""
    if not is_enabled():
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_open_app"), web_app=_info())]
        ]
    )


def menu_button() -> MenuButtonWebApp | MenuButtonCommands:
    """Kiritish maydoni yonidagi doimiy tugma.

    WEBAPP_URL bo'lmasa oddiy buyruqlar menyusiga qaytariladi — aks holda
    manzil o'chirilgach eski tugma osilib qolardi.
    """
    if not is_enabled():
        return MenuButtonCommands()
    return MenuButtonWebApp(text=t("uz", "menu_button_app"), web_app=_info())
