import logging
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.crud import (
    confirm_report, get_report_by_id, get_unconfirmed_reports, reject_report
)
from database.models import User
from database.session import AsyncSessionLocal
from filters.roles import IsAdmin
from keyboards.admin_kb import attendance_approve_kb
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


@router.message(F.text.in_(["✅ Davomat tasdiqlash", "✅ Подтверждение посещаемости"]))
async def attendance_menu(
    message: Message, state: FSMContext, db_user: Optional[User] = None
):
    lang = db_user.language

    async with AsyncSessionLocal() as session:
        reports = await get_unconfirmed_reports(session)

    if not reports:
        await message.answer(t(lang, "no_pending"))
        return

    await message.answer(t(lang, "attendance_menu"))
    for report in reports:
        await message.answer(
            build_report_caption(lang, report),
            parse_mode="HTML",
            reply_markup=attendance_approve_kb(lang, report.id),
        )


@router.callback_query(F.data.startswith("att_approve:"))
async def approve_report(
    callback: CallbackQuery, state: FSMContext, bot: Bot,
    db_user: Optional[User] = None,
):
    lang = db_user.language
    report_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, report_id)

    if not report:
        await callback.answer(t(lang, "report_not_found"), show_alert=True)
        return
    if report.is_confirmed or report.is_rejected:
        await callback.answer(t(lang, "report_already_processed"), show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
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
        return

    logger.info("Hisobot #%s tasdiqlandi, admin id=%s", report_id, db_user.id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "report_approved"))
    await callback.answer("✅")

    if report.user.telegram_id is not None:
        await notify_user(
            bot, report.user.telegram_id,
            t(report.user.language, "report_approved_notify"),
        )


@router.callback_query(F.data.startswith("att_reject:"))
async def reject_report_handler(
    callback: CallbackQuery, state: FSMContext, bot: Bot,
    db_user: Optional[User] = None,
):
    lang = db_user.language
    report_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        report = await reject_report(session, report_id, db_user.id)

    if report is None:
        await callback.answer(t(lang, "report_already_processed"), show_alert=True)
        return

    logger.info("Hisobot #%s rad etildi, admin id=%s", report_id, db_user.id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "report_rejected"))
    await callback.answer()

    if report.user.telegram_id is not None:
        await notify_user(
            bot, report.user.telegram_id,
            t(report.user.language, "report_rejected_notify"),
        )
