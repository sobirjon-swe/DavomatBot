from datetime import date
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_today_reports,
    get_reports_by_date_and_user, get_all_users, get_report_by_id
)
from database.models import UserRole
from keyboards.admin_kb import (
    reports_section_kb, view_photos_kb, employees_list_kb
)
from locales import t
from states.admin import AdminReportStates
from utils.formatters import build_report_caption

router = Router()


@router.message(F.text.in_(["📊 Hisobotlar", "📊 Отчёты"]))
async def reports_menu(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user or user.role not in (UserRole.admin, UserRole.superadmin):
        return

    lang = user.language
    await message.answer(t(lang, "reports_menu"), reply_markup=reports_section_kb(lang))


@router.callback_query(F.data == "rpt:today")
async def today_reports(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        reports = await get_today_reports(session)

    lang = admin.language
    if not reports:
        await callback.message.edit_text(t(lang, "no_reports"))
        await callback.answer()
        return

    await callback.message.edit_text(t(lang, "btn_today_reports"))
    for report in reports:
        caption = build_report_caption(lang, report)
        await callback.message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=view_photos_kb(lang, report.id) if report.photos else None,
        )
    await callback.answer()


@router.callback_query(F.data == "rpt:search")
async def search_reports_start(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
    lang = admin.language
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "search_date"))
    await state.set_state(AdminReportStates.entering_date)
    await callback.answer()


@router.message(AdminReportStates.entering_date)
async def search_enter_date(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    date_str = message.text.strip()

    try:
        parts = date_str.split(".")
        search_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        await message.answer(t(lang, "invalid_date"))
        return

    await state.update_data(search_date=search_date.isoformat())

    async with AsyncSessionLocal() as session:
        all_users = await get_all_users(session)

    employees = [u for u in all_users if u.is_active]
    await message.answer(
        t(lang, "search_employee"),
        reply_markup=employees_list_kb(lang, employees),
    )
    await state.set_state(AdminReportStates.choosing_employee)


@router.callback_query(AdminReportStates.choosing_employee, F.data.startswith("sel_emp:"))
async def search_choose_employee(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    user_id = int(callback.data.split(":")[1])
    search_date_str = data.get("search_date")
    search_date_obj = date.fromisoformat(search_date_str)

    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        reports = await get_reports_by_date_and_user(session, search_date_obj, user_id)

    lang = admin.language
    if not reports:
        await callback.message.edit_text(t(lang, "no_reports"))
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(t(lang, "btn_search_reports"))
    for report in reports:
        caption = build_report_caption(lang, report)
        await callback.message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=view_photos_kb(lang, report.id) if report.photos else None,
        )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("rpt_photos:"))
async def view_report_photos(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        report = await get_report_by_id(session, report_id)

    if not report or not report.photos:
        await callback.answer("Rasmlar topilmadi.", show_alert=True)
        return

    lang = admin.language
    photo_ids = [p.file_id for p in report.photos]

    if len(photo_ids) == 1:
        await callback.message.answer_photo(photo=photo_ids[0])
    else:
        media = [InputMediaPhoto(media=fid) for fid in photo_ids]
        await callback.message.answer_media_group(media=media)

    await callback.answer()
