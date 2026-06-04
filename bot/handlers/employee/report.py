from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_all_active_employees,
    get_all_districts, create_report, add_report_partners,
    add_report_photos, get_report_by_id
)
from database.models import ReportType
from keyboards.employee_kb import (
    report_type_kb, report_subtype_kb, partners_kb, single_district_kb,
    location_kb, photos_kb, plots_kb, confirm_report_kb, main_menu_kb,
    remove_kb
)
from locales import t
from states.report import ReportStates
from utils.formatters import (
    format_report_type, format_partners, format_datetime, format_district_name
)
from utils.notifications import notify_partners

router = Router()


@router.message(F.text.in_(["📋 Ma'lumot berish", "📋 Подать отчёт"]))
async def start_report(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        return

    lang = user.language
    await message.answer(t(lang, "choose_report_type"), reply_markup=report_type_kb(lang))
    await state.set_state(ReportStates.choosing_type)
    await state.update_data(user_id=user.id, lang=lang)


@router.callback_query(ReportStates.choosing_type, F.data.startswith("report_type:"))
async def choose_report_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    rtype = callback.data.split(":")[1]

    if rtype == "laboratory":
        await state.update_data(report_type=ReportType.laboratory)
        await _show_partners(callback, state, lang)
    else:
        await callback.message.edit_text(
            t(lang, "choose_report_type"),
            reply_markup=report_subtype_kb(lang),
        )
        await state.set_state(ReportStates.choosing_subtype)
    await callback.answer()


@router.callback_query(ReportStates.choosing_subtype, F.data.startswith("report_subtype:"))
async def choose_report_subtype(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    subtype = callback.data.split(":")[1]

    rtype = ReportType.visual if subtype == "visual" else ReportType.instrumental
    await state.update_data(report_type=rtype)
    await _show_partners(callback, state, lang)
    await callback.answer()


async def _show_partners(callback: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    user_id = data.get("user_id")

    async with AsyncSessionLocal() as session:
        all_employees = await get_all_active_employees(session)

    employees = [e for e in all_employees if e.id != user_id]
    await state.update_data(selected_partner_ids=[], all_employees=[
        {"id": e.id, "full_name": e.full_name} for e in employees
    ])

    await callback.message.edit_text(
        t(lang, "choose_partners"),
        reply_markup=partners_kb(lang, employees, []),
    )
    await state.set_state(ReportStates.choosing_partners)


@router.callback_query(ReportStates.choosing_partners, F.data.startswith("partner:"))
async def toggle_partner(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    action = callback.data.split(":")[1]

    if action in ("none", "done"):
        await _show_districts(callback, state, lang)
        await callback.answer()
        return

    partner_id = int(action)
    selected = data.get("selected_partner_ids", [])
    if partner_id in selected:
        selected.remove(partner_id)
    else:
        selected.append(partner_id)
    await state.update_data(selected_partner_ids=selected)

    async with AsyncSessionLocal() as session:
        employees = await get_all_active_employees(session)
    user_id = data.get("user_id")
    employees = [e for e in employees if e.id != user_id]

    await callback.message.edit_reply_markup(
        reply_markup=partners_kb(lang, employees, selected)
    )
    await callback.answer()


async def _show_districts(callback: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    user_id = data.get("user_id")

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(
            session, callback.from_user.id
        )
        user_district_ids = [ud.district_id for ud in user.user_districts]
        all_districts = await get_all_active_districts_for_user(session, user_district_ids)

    await state.update_data(user_district_ids=user_district_ids)
    await callback.message.edit_text(
        t(lang, "choose_district"),
        reply_markup=single_district_kb(lang, all_districts),
    )
    await state.set_state(ReportStates.choosing_district)


async def get_all_active_districts_for_user(session, district_ids: list):
    from sqlalchemy import select
    from database.models import District
    result = await session.execute(
        select(District).where(District.id.in_(district_ids)).order_by(District.id)
    )
    return list(result.scalars().all())


@router.callback_query(ReportStates.choosing_district, F.data == "single_dist:other")
async def choose_other_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from database.models import District
        result = await session.execute(select(District).order_by(District.id))
        all_districts = list(result.scalars().all())

    await callback.message.edit_text(
        t(lang, "choose_district"),
        reply_markup=single_district_kb(lang, all_districts, show_other=False),
    )
    await callback.answer()


@router.callback_query(ReportStates.choosing_district, F.data.startswith("single_dist:"))
async def choose_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    district_id = int(callback.data.split(":")[1])
    await state.update_data(district_id=district_id)

    await callback.message.edit_text(t(lang, "enter_customer"))
    await state.set_state(ReportStates.entering_customer)
    await callback.answer()


@router.message(ReportStates.entering_customer)
async def enter_customer(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(customer_name=message.text.strip())
    await message.answer(t(lang, "send_location"), reply_markup=location_kb(lang))
    await state.set_state(ReportStates.sending_location)


@router.message(ReportStates.sending_location, F.location)
async def receive_location(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(
        location_lat=message.location.latitude,
        location_lon=message.location.longitude,
        photo_file_ids=[],
    )
    await message.answer(
        t(lang, "send_photos"),
        reply_markup=remove_kb(),
    )
    await state.set_state(ReportStates.sending_photos)


@router.message(ReportStates.sending_photos, F.photo)
async def receive_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    photo_ids = data.get("photo_file_ids", [])

    if len(photo_ids) >= 7:
        await message.answer(t(lang, "min_photos_required"))
        return

    largest = message.photo[-1]
    photo_ids.append(largest.file_id)
    await state.update_data(photo_file_ids=photo_ids)
    count = len(photo_ids)

    await message.answer(
        t(lang, "photos_progress", count=count),
        reply_markup=photos_kb(lang, count),
    )


@router.callback_query(ReportStates.sending_photos, F.data == "photos:done")
async def photos_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    count = len(data.get("photo_file_ids", []))

    if count < 3:
        await callback.answer(t(lang, "min_photos_required"), show_alert=True)
        return

    report_type = data.get("report_type")
    if report_type == ReportType.laboratory:
        await callback.message.edit_text(
            t(lang, "enter_plots_count"),
            reply_markup=plots_kb(lang),
        )
        await state.set_state(ReportStates.entering_plots)
    else:
        await state.update_data(plots_count=None)
        await _show_preview(callback.message, state, lang)

    await callback.answer()


@router.message(ReportStates.entering_plots)
async def enter_plots_count(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    try:
        plots = int(message.text.strip())
        await state.update_data(plots_count=plots)
    except ValueError:
        await message.answer(t(lang, "error_generic"))
        return
    await _show_preview(message, state, lang)


@router.callback_query(ReportStates.entering_plots, F.data == "plots:skip")
async def skip_plots(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(plots_count=None)
    await _show_preview(callback.message, state, lang)
    await callback.answer()


async def _show_preview(message: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    report_type = data.get("report_type")
    district_id = data.get("district_id")
    customer_name = data.get("customer_name")
    partner_ids = data.get("selected_partner_ids", [])
    photo_ids = data.get("photo_file_ids", [])
    plots_count = data.get("plots_count")

    async with AsyncSessionLocal() as session:
        from database.models import District
        from sqlalchemy import select
        district = (await session.execute(
            select(District).where(District.id == district_id)
        )).scalar_one_or_none()

        all_employees = await get_all_active_employees(session)
        partner_names = [e.full_name for e in all_employees if e.id in partner_ids]

    district_name = district.name_uz if lang == "uz" else district.name_ru
    type_text = format_report_type(lang, report_type)
    partners_text = ", ".join(partner_names) if partner_names else "—"
    now = datetime.now().strftime("%d.%m.%Y | %H:%M")

    from utils.formatters import format_location_url
    location_lat = data.get("location_lat")
    location_lon = data.get("location_lon")
    location_str = format_location_url(location_lat, location_lon) if location_lat and location_lon else "—"

    preview = t(
        lang, "report_preview",
        report_type=type_text,
        district=district_name,
        customer=customer_name,
        partners=partners_text,
        photos_count=len(photo_ids),
        date=now,
        location=location_str,
    )
    if plots_count is not None:
        preview += t(lang, "report_preview_plots", plots_count=plots_count)

    await message.answer(
        preview,
        parse_mode="HTML",
        reply_markup=confirm_report_kb(lang),
    )
    await state.set_state(ReportStates.confirming)


@router.callback_query(ReportStates.confirming, F.data == "report:refill")
async def refill_report(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    user_id = data.get("user_id")
    await state.clear()
    await state.update_data(user_id=user_id, lang=lang)
    await callback.message.edit_text(t(lang, "choose_report_type"), reply_markup=report_type_kb(lang))
    await state.set_state(ReportStates.choosing_type)
    await callback.answer()


@router.callback_query(ReportStates.confirming, F.data == "report:submit")
async def submit_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    async with AsyncSessionLocal() as session:
        report = await create_report(
            session,
            user_id=data["user_id"],
            report_type=data["report_type"],
            district_id=data["district_id"],
            customer_name=data["customer_name"],
            location_lat=data["location_lat"],
            location_lon=data["location_lon"],
            plots_count=data.get("plots_count"),
        )
        partner_ids = data.get("selected_partner_ids", [])
        await add_report_partners(session, report.id, partner_ids)
        await add_report_photos(session, report.id, data.get("photo_file_ids", []))
        await session.commit()
        report_full = await get_report_by_id(session, report.id)

    await callback.message.edit_text(t(lang, "report_submitted"))

    async with AsyncSessionLocal() as session:
        report_full = await get_report_by_id(session, report.id)
        await notify_partners(bot, report_full, lang)

    from keyboards.employee_kb import main_menu_kb
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)

    await callback.message.answer(
        t(lang, "main_menu"),
        reply_markup=main_menu_kb(lang),
    )
    await state.clear()
    await callback.answer()
