from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import config
from keyboards import webapp
from locales import t


def language_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek", callback_data="lang:uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.adjust(2)
    return builder.as_markup()


def link_accounts_kb(lang: str, users: list) -> InlineKeyboardMarkup:
    """Admin oldindan qo'shgan, hali egasi bo'lmagan hodim yozuvlari."""
    builder = InlineKeyboardBuilder()
    for user in users:
        builder.button(
            text=f"{user.full_name} — {user.position}",
            callback_data=f"link:{user.id}",
        )
    builder.button(text=t(lang, "btn_not_in_list"), callback_data="link:new")
    builder.adjust(1)
    return builder.as_markup()


def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=t(lang, "btn_report"))
    builder.button(text=t(lang, "btn_settings"))

    app_button = webapp.reply_button(lang)
    if app_button is not None:
        builder.add(app_button)
        # Ilova tugmasi alohida qatorda — u boshqa turdagi amal
        builder.adjust(2, 1)
    else:
        builder.adjust(2)

    return builder.as_markup(resize_keyboard=True)


def settings_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_edit_districts"), callback_data="settings:districts")
    builder.button(text=t(lang, "btn_change_language"), callback_data="settings:language")
    builder.adjust(1)
    return builder.as_markup()


def report_type_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_laboratory"), callback_data="report_type:laboratory")
    builder.button(text=t(lang, "btn_technical"), callback_data="report_type:technical")
    builder.adjust(1)
    return builder.as_markup()


def report_subtype_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_visual"), callback_data="report_subtype:visual")
    builder.button(text=t(lang, "btn_instrumental"), callback_data="report_subtype:instrumental")
    builder.adjust(1)
    return builder.as_markup()


def partners_kb(lang: str, employees: list, selected_ids: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for emp in employees:
        check = "✅" if emp.id in selected_ids else "◻️"
        builder.button(
            text=f"{check} {emp.full_name}",
            callback_data=f"partner:{emp.id}"
        )
    builder.button(text=t(lang, "btn_no_partner"), callback_data="partner:none")
    builder.button(text=t(lang, "btn_continue"), callback_data="partner:done")
    builder.adjust(1)
    return builder.as_markup()


def districts_kb(
    lang: str,
    districts: list,
    selected_ids: list[int],
    confirm_text: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for district in districts:
        name = district.name_uz if lang == "uz" else district.name_ru
        check = "✅" if district.id in selected_ids else "◻️"
        builder.button(
            text=f"{check} {name}",
            callback_data=f"dist:{district.id}"
        )
    confirm_label = confirm_text or t(lang, "btn_continue")
    builder.button(text=confirm_label, callback_data="dist:done")
    builder.adjust(1)
    return builder.as_markup()


def single_district_kb(lang: str, districts: list, show_other: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for district in districts:
        name = district.name_uz if lang == "uz" else district.name_ru
        builder.button(text=name, callback_data=f"single_dist:{district.id}")
    if show_other:
        builder.button(
            text=t(lang, "btn_other_district"), callback_data="single_dist:other"
        )
    builder.adjust(2)
    return builder.as_markup()


def location_kb(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=t(lang, "btn_send_location"), request_location=True)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def photos_kb(lang: str, count: int) -> InlineKeyboardMarkup:
    """Yetarli rasm yuborilgandagina "Tayyor" tugmasi ko'rsatiladi."""
    builder = InlineKeyboardBuilder()
    if count >= config.MIN_REPORT_PHOTOS:
        builder.button(text=t(lang, "btn_done"), callback_data="photos:done")
    builder.adjust(1)
    return builder.as_markup()


def plots_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_skip"), callback_data="plots:skip")
    builder.adjust(1)
    return builder.as_markup()


def confirm_report_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_submit"), callback_data="report:submit")
    builder.button(text=t(lang, "btn_refill"), callback_data="report:refill")
    builder.adjust(2)
    return builder.as_markup()


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
