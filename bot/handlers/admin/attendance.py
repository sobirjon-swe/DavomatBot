import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from database.crud import (
    confirm_report,
    count_unconfirmed_reports,
    get_report_by_id,
    get_unconfirmed_reports,
    reject_report,
)
from database.models import User
from database.session import AsyncSessionLocal
from filters.roles import IsAdmin
from keyboards.admin_kb import attendance_approve_kb
from keyboards.pagination import clamp, nav_row, page_count
from locales import t
from utils.channel import send_report_to_channel
from utils.formatters import build_report_caption, esc
from utils.notifications import notify_user

logger = logging.getLogger(__name__)

router = Router()
# Ruxsat butun router uchun bir joyda tekshiriladi: inline tugmalar ham
# himoyalanadi, ilgari faqat menyu tugmasi tekshirilardi.
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _card_kb(lang: str, report_id: int, page: int, pages: int) -> InlineKeyboardMarkup:
    """Tasdiqlash tugmalari va sahifalar bo'ylab navigatsiya."""
    markup = attendance_approve_kb(lang, report_id, page)
    if pages > 1:
        markup.inline_keyboard.append(nav_row("att_page", page, pages))
    return markup


async def _render_page(message: Message, lang: str, page: int, *, edit: bool) -> None:
    """Kutayotgan hisobotlarni bittalab ko'rsatadi.

    Ilgari hammasi birdan alohida xabar bo'lib yuborilardi — 30 ta
    tasdiqlanmagan hisobot 30 ta xabar degani edi.
    """
    async with AsyncSessionLocal() as session:
        total = await count_unconfirmed_reports(session)
        if total == 0:
            text = t(lang, "no_pending")
            if edit:
                await message.edit_text(text)
            else:
                await message.answer(text)
            return

        pages = page_count(total, per_page=1)
        page = clamp(page, pages)
        reports = await get_unconfirmed_reports(session, offset=page - 1, limit=1)

    report = reports[0]
    text = (
        t(lang, "pending_list_header", total=total)
        + "\n\n"
        + build_report_caption(lang, report)
    )
    markup = _card_kb(lang, report.id, page, pages)

    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.message(F.text.in_(["✅ Davomat tasdiqlash", "✅ Подтверждение посещаемости"]))
async def attendance_menu(
    message: Message, state: FSMContext, db_user: User | None = None
):
    await _render_page(message, db_user.language, 1, edit=False)


@router.callback_query(F.data.startswith("att_page:"))
async def attendance_page(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    page = int(callback.data.split(":")[1])
    await _render_page(callback.message, db_user.language, page, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("att_approve:"))
async def approve_report(
    callback: CallbackQuery, state: FSMContext, bot: Bot,
    db_user: User | None = None,
):
    lang = db_user.language
    _, raw_id, raw_page = callback.data.split(":")
    report_id, page = int(raw_id), int(raw_page)

    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, report_id)

    if not report:
        await callback.answer(t(lang, "report_not_found"), show_alert=True)
        return
    if report.is_confirmed or report.is_rejected:
        await callback.answer(t(lang, "report_already_processed"), show_alert=True)
        await _render_page(callback.message, lang, page, edit=True)
        return

    ok, error = await send_report_to_channel(bot, report)
    if not ok:
        # Kanalga bormagan hisobot tasdiqlangan deb belgilanmaydi.
        await callback.message.answer(
            t(lang, "channel_send_failed", error=esc((error or "")[:200])),
            parse_mode="HTML",
        )
        await callback.answer(t(lang, "report_not_approved"), show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        confirmed = await confirm_report(session, report_id, db_user.id)

    if confirmed is None:
        await callback.answer(t(lang, "report_already_processed"), show_alert=True)
        await _render_page(callback.message, lang, page, edit=True)
        return

    logger.info("Hisobot #%s tasdiqlandi, admin id=%s", report_id, db_user.id)
    await callback.answer(t(lang, "report_approved"))

    if report.user.telegram_id is not None:
        await notify_user(
            bot, report.user.telegram_id,
            t(report.user.language, "report_approved_notify"),
        )

    # Ro'yxatdan bittasi chiqdi — o'sha o'rinda endi keyingisi turadi.
    await _render_page(callback.message, lang, page, edit=True)


@router.callback_query(F.data.startswith("att_reject:"))
async def reject_report_handler(
    callback: CallbackQuery, state: FSMContext, bot: Bot,
    db_user: User | None = None,
):
    lang = db_user.language
    _, raw_id, raw_page = callback.data.split(":")
    report_id, page = int(raw_id), int(raw_page)

    async with AsyncSessionLocal() as session:
        report = await reject_report(session, report_id, db_user.id)

    if report is None:
        await callback.answer(t(lang, "report_already_processed"), show_alert=True)
        await _render_page(callback.message, lang, page, edit=True)
        return

    logger.info("Hisobot #%s rad etildi, admin id=%s", report_id, db_user.id)
    await callback.answer(t(lang, "report_rejected"))

    if report.user.telegram_id is not None:
        await notify_user(
            bot, report.user.telegram_id,
            t(report.user.language, "report_rejected_notify"),
        )

    await _render_page(callback.message, lang, page, edit=True)
