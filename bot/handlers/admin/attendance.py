from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_unconfirmed_reports,
    confirm_report, reject_report, get_report_by_id
)
from database.models import UserRole
from keyboards.admin_kb import attendance_approve_kb
from locales import t
from utils.channel import send_report_to_channel
from utils.formatters import build_report_caption

router = Router()


@router.message(F.text.in_(["✅ Davomat tasdiqlash", "✅ Подтверждение посещаемости"]))
async def attendance_menu(message: Message, state: FSMContext, bot: Bot):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user or user.role not in (UserRole.admin, UserRole.superadmin):
        return

    lang = user.language
    async with AsyncSessionLocal() as session:
        reports = await get_unconfirmed_reports(session)

    if not reports:
        await message.answer(t(lang, "no_pending"))
        return

    await message.answer(t(lang, "attendance_menu"))
    for report in reports:
        caption = build_report_caption(lang, report)
        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=attendance_approve_kb(lang, report.id),
        )


@router.callback_query(F.data.startswith("att_approve:"))
async def approve_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    report_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        report_full = await get_report_by_id(session, report_id)

    if not report_full:
        await callback.answer("Hisobot topilmadi.", show_alert=True)
        return

    lang = admin.language

    result = await send_report_to_channel(bot, report_full)

    if result is not True:
        await callback.message.answer(f"❌ Kanalga yuborishda xato:\n<code>{result}</code>", parse_mode="HTML")
        await callback.answer("❌ Hisobot tasdiqlanmadi.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        await confirm_report(session, report_id, admin.id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "report_approved"))
    await callback.answer("✅")


@router.callback_query(F.data.startswith("att_reject:"))
async def reject_report_handler(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        success = await reject_report(session, report_id)

    lang = admin.language
    if not success:
        await callback.answer("Hisobot topilmadi.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "report_rejected"))
    await callback.answer()
