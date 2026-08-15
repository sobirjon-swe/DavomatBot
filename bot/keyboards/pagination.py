import math

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales import t

# Bitta sahifadagi yozuvlar soni. Telegram bitta xabar matnini 4096 belgi
# bilan cheklaydi, tugmalar esa qulay bo'lishi kerak.
PER_PAGE = 5


def page_count(total: int, per_page: int = PER_PAGE) -> int:
    return max(1, math.ceil(total / per_page))


def clamp(page: int, pages: int) -> int:
    """Sahifa raqamini chegaraga soladi.

    Eski xabardagi tugma bosilganda ro'yxat qisqargan bo'lishi mumkin,
    shuning uchun kelgan raqamga ishonmaymiz.
    """
    return min(max(page, 1), pages)


def offset_of(page: int, per_page: int = PER_PAGE) -> int:
    return (page - 1) * per_page


def nav_row(page_prefix: str, page: int, pages: int) -> list[InlineKeyboardButton]:
    """Oldingi / sahifa raqami / keyingi tugmalari.

    Chekkadagi tugmalar "noop" ga ishora qiladi — bosilganda hech nima
    o'zgarmaydi, lekin klaviatura shakli buzilmaydi.
    """
    return [
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"{page_prefix}:{page - 1}" if page > 1 else "noop",
        ),
        InlineKeyboardButton(text=f"{page}/{pages}", callback_data="noop"),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"{page_prefix}:{page + 1}" if page < pages else "noop",
        ),
    ]


def list_page_kb(
    *,
    open_prefix: str,
    page_prefix: str,
    page: int,
    pages: int,
    items: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    """Sahifadagi yozuvlar uchun tugmalar va navigatsiya qatori.

    `items` — (id, ko'rinadigan matn) juftliklari. Har biri
    `{open_prefix}:{id}:{page}` callback ini beradi, shunda kartochkadan
    aynan shu sahifaga qaytib kelish mumkin.
    """
    builder = InlineKeyboardBuilder()
    for item_id, label in items:
        builder.button(text=label, callback_data=f"{open_prefix}:{item_id}:{page}")
    builder.adjust(1)

    if pages > 1:
        builder.row(*nav_row(page_prefix, page, pages))

    return builder.as_markup()


def with_back_button(
    lang: str,
    page_prefix: str,
    page: int,
    extra: InlineKeyboardMarkup | None = None,
) -> InlineKeyboardMarkup:
    """Kartochka tugmalariga "ro'yxatga qaytish" qatorini qo'shadi."""
    builder = InlineKeyboardBuilder()
    if extra is not None:
        for row in extra.inline_keyboard:
            builder.row(*row)
    builder.row(
        InlineKeyboardButton(
            text=t(lang, "btn_back_to_list"),
            callback_data=f"{page_prefix}:{page}",
        )
    )
    return builder.as_markup()
