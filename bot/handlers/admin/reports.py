from datetime import date, datetime
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from database.crud import (
    get_all_users, get_report_by_id, get_reports_by_date_and_user, get_today_reports
)
from database.models import User
from database.session import AsyncSessionLocal
from filters.roles import IsAdmin
from keyboards.admin_kb import employees_list_kb, reports_section_kb, view_photos_kb
from locales import t
from states.admin import AdminReportStates
from utils.formatters import build_report_caption
from utils.messages import text_of

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _send_report_cards(message: Message, lang: str, reports: list) -> None:
    for report in reports:
        await message.answer(
            build_report_caption(lang, report),
            parse_mode="HTML",
            reply_markup=view_photos_kb(lang, report.id) if report.photos else None,
        )


@router.message(F.text.in_(["📊 Hisobotlar", "📊 Отчёты"]))
async def reports_menu(
    message: Message, state: FSMContext, db_user: Optional[User] = None
):
    await message.answer(
        t(db_user.language, "reports_menu"),
        reply_markup=reports_section_kb(db_user.language),
    )


@router.callback_query(F.data == "rpt:today")
async def today_reports(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    lang = db_user.language

    async with AsyncSessionLocal() as session:
        reports = await get_today_reports(session)

    if not reports:
        await callback.message.edit_text(t(lang, "no_reports"))
        await callback.answer()
        return

    await callback.message.edit_text(t(lang, "btn_today_reports"))
    await _send_report_cards(callback.message, lang, reports)
    await callback.answer()


@router.callback_query(F.data == "rpt:search")
async def search_reports_start(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    lang = db_user.language
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "search_date"))
    await state.set_state(AdminReportStates.entering_date)
    await callback.answer()


@router.message(AdminReportStates.entering_date)
async def search_enter_date(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    raw = text_of(message)
    if raw is None:
        await message.answer(t(lang, "text_expected"))
        return

    try:
        search_date = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(t(lang, "invalid_date"))
        return

    await state.update_data(search_date=search_date.isoformat())

    async with AsyncSessionLocal() as session:
        all_users = await get_all_users(session)

    employees = [u for u in all_users if u.is_active]
    if not employees:
        await message.answer(t(lang, "no_employees"))
        await state.clear()
        return

    await message.answer(
        t(lang, "search_employee"),
        reply_markup=employees_list_kb(lang, employees),
    )
    await state.set_state(AdminReportStates.choosing_employee)


@router.callback_query(AdminReportStates.choosing_employee, F.data.startswith("sel_emp:"))
async def search_choose_employee(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    data = await state.get_data()
    lang = db_user.language
    user_id = int(callback.data.split(":")[1])
    search_date = date.fromisoformat(data["search_date"])

    async with AsyncSessionLocal() as session:
        reports = await get_reports_by_date_and_user(session, search_date, user_id)

    if not reports:
        await callback.message.edit_text(t(lang, "no_reports"))
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(t(lang, "btn_search_reports"))
    await _send_report_cards(callback.message, lang, reports)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("rpt_photos:"))
async def view_report_photos(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    report_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, report_id)

    if not report or not report.photos:
        await callback.answer(t(db_user.language, "no_photos"), show_alert=True)
        return

    photo_ids = [p.file_id for p in report.photos]
    if len(photo_ids) == 1:
        await callback.message.answer_photo(photo=photo_ids[0])
    else:
        await callback.message.answer_media_group(
            media=[InputMediaPhoto(media=fid) for fid in photo_ids]
        )
    await callback.answer()
