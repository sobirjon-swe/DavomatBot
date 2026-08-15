import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
from database.crud import (
    add_report_partners,
    add_report_photos,
    create_report,
    get_all_active_employees,
    get_all_districts,
    get_district_by_id,
    get_districts_by_ids,
    get_report_by_id,
    get_user_by_id,
    get_user_district_ids,
)
from database.models import ReportType, User
from database.session import AsyncSessionLocal
from keyboards.employee_kb import (
    confirm_report_kb,
    location_kb,
    main_menu_kb,
    partners_kb,
    photos_kb,
    plots_kb,
    remove_kb,
    report_subtype_kb,
    report_type_kb,
    single_district_kb,
)
from locales import t
from states.report import ReportStates
from utils.formatters import TASHKENT_TZ, esc, format_location_url, format_report_type
from utils.menu_texts import RESERVED_MENU_TEXTS
from utils.messages import text_of
from utils.notifications import notify_partners

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["📋 Ma'lumot berish", "📋 Подать отчёт"]))
async def start_report(
    message: Message, state: FSMContext, db_user: User | None = None
):
    if not db_user or not db_user.is_active:
        return

    lang = db_user.language
    await state.set_state(ReportStates.choosing_type)
    await state.update_data(user_id=db_user.id, lang=lang)
    await message.answer(t(lang, "choose_report_type"), reply_markup=report_type_kb(lang))


@router.callback_query(ReportStates.choosing_type, F.data.startswith("report_type:"))
async def choose_report_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    if callback.data.split(":")[1] == "laboratory":
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


async def _load_partner_candidates(exclude_user_id: int) -> list[User]:
    async with AsyncSessionLocal() as session:
        employees = await get_all_active_employees(session)
    return [e for e in employees if e.id != exclude_user_id]


async def _show_partners(callback: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    employees = await _load_partner_candidates(data.get("user_id"))

    await state.update_data(selected_partner_ids=[])
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

    if action == "none":
        # "Sherik yo'q" avval belgilanganlarni ham bekor qiladi.
        await state.update_data(selected_partner_ids=[])
        await _show_districts(callback, state, lang)
        await callback.answer()
        return

    if action == "done":
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

    employees = await _load_partner_candidates(data.get("user_id"))
    await callback.message.edit_reply_markup(
        reply_markup=partners_kb(lang, employees, selected)
    )
    await callback.answer()


async def _show_districts(callback: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        district_ids = await get_user_district_ids(session, data.get("user_id"))
        districts = await get_districts_by_ids(session, district_ids)
        # Hodimga tuman biriktirilmagan bo'lsa, tugmasiz ekran chiqmasligi
        # uchun to'liq ro'yxat ko'rsatiladi.
        if not districts:
            districts = await get_all_districts(session)

    await callback.message.edit_text(
        t(lang, "choose_district"),
        reply_markup=single_district_kb(lang, districts),
    )
    await state.set_state(ReportStates.choosing_district)


@router.callback_query(ReportStates.choosing_district, F.data == "single_dist:other")
async def choose_other_district(callback: CallbackQuery, state: FSMContext):
    """Biriktirilmagan hududda ish bo'lsa, to'liq ro'yxatni ko'rsatadi."""
    data = await state.get_data()
    lang = data.get("lang", "uz")

    async with AsyncSessionLocal() as session:
        all_districts = await get_all_districts(session)

    await callback.message.edit_text(
        t(lang, "choose_district"),
        reply_markup=single_district_kb(lang, all_districts, show_other=False),
    )
    await callback.answer()


@router.callback_query(ReportStates.choosing_district, F.data.startswith("single_dist:"))
async def choose_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    await state.update_data(district_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text(t(lang, "enter_customer"))
    await state.set_state(ReportStates.entering_customer)
    await callback.answer()


@router.message(ReportStates.entering_customer, ~F.text.in_(RESERVED_MENU_TEXTS))
async def enter_customer(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    customer = text_of(message)
    if not customer:
        await message.answer(t(lang, "text_expected"))
        return

    await state.update_data(customer_name=customer)
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
        t(lang, "send_photos",
          min=config.MIN_REPORT_PHOTOS, max=config.MAX_REPORT_PHOTOS),
        reply_markup=remove_kb(),
    )
    await state.set_state(ReportStates.sending_photos)


@router.message(ReportStates.sending_location, ~F.text.in_(RESERVED_MENU_TEXTS))
async def location_expected(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(t(data.get("lang", "uz"), "location_expected"))


@router.message(ReportStates.sending_photos, F.photo)
async def receive_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    photo_ids = data.get("photo_file_ids", [])

    if len(photo_ids) >= config.MAX_REPORT_PHOTOS:
        await message.answer(t(lang, "max_photos_reached", max=config.MAX_REPORT_PHOTOS))
        return

    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=photo_ids)

    await message.answer(
        t(lang, "photos_progress",
          count=len(photo_ids), min=config.MIN_REPORT_PHOTOS),
        reply_markup=photos_kb(lang, len(photo_ids)),
    )


@router.callback_query(ReportStates.sending_photos, F.data == "photos:done")
async def photos_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    if len(data.get("photo_file_ids", [])) < config.MIN_REPORT_PHOTOS:
        await callback.answer(
            t(lang, "min_photos_required", min=config.MIN_REPORT_PHOTOS),
            show_alert=True,
        )
        return

    if data.get("report_type") == ReportType.laboratory:
        await callback.message.edit_text(
            t(lang, "enter_plots_count"),
            reply_markup=plots_kb(lang),
        )
        await state.set_state(ReportStates.entering_plots)
    else:
        await state.update_data(plots_count=None)
        await _show_preview(callback.message, state, lang)

    await callback.answer()


@router.message(ReportStates.entering_plots, ~F.text.in_(RESERVED_MENU_TEXTS))
async def enter_plots_count(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    raw = text_of(message)
    if raw is None or not raw.isdigit():
        await message.answer(t(lang, "invalid_number"))
        return

    await state.update_data(plots_count=int(raw))
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
    partner_ids = data.get("selected_partner_ids", [])

    async with AsyncSessionLocal() as session:
        district = await get_district_by_id(session, data.get("district_id"))
        employees = await get_all_active_employees(session)

    partner_names = [esc(e.full_name) for e in employees if e.id in partner_ids]
    district_name = district.name_uz if lang == "uz" else district.name_ru

    lat, lon = data.get("location_lat"), data.get("location_lon")
    location_str = format_location_url(lat, lon) if lat is not None else "—"

    preview = t(
        lang, "report_preview",
        report_type=format_report_type(lang, data.get("report_type")),
        district=esc(district_name),
        customer=esc(data.get("customer_name")),
        partners=", ".join(partner_names) if partner_names else "—",
        photos_count=len(data.get("photo_file_ids", [])),
        date=datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y | %H:%M"),
        location=location_str,
    )
    plots_count = data.get("plots_count")
    if plots_count is not None:
        preview += t(lang, "report_preview_plots", plots_count=plots_count)

    await message.answer(
        preview, parse_mode="HTML", reply_markup=confirm_report_kb(lang)
    )
    await state.set_state(ReportStates.confirming)


@router.callback_query(ReportStates.confirming, F.data == "report:refill")
async def refill_report(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    user_id = data.get("user_id")

    await state.clear()
    await state.update_data(user_id=user_id, lang=lang)
    await callback.message.edit_text(
        t(lang, "choose_report_type"), reply_markup=report_type_kb(lang)
    )
    await state.set_state(ReportStates.choosing_type)
    await callback.answer()


@router.callback_query(ReportStates.confirming, F.data == "report:submit")
async def submit_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    async with AsyncSessionLocal() as session:
        current_user = await get_user_by_id(session, data["user_id"])
        if not current_user or not current_user.is_active:
            await callback.message.edit_text(t(lang, "account_deactivated"))
            await state.clear()
            await callback.answer()
            return

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
        await add_report_partners(session, report.id, data.get("selected_partner_ids", []))
        await add_report_photos(session, report.id, data.get("photo_file_ids", []))
        await session.commit()
        report_full = await get_report_by_id(session, report.id)

    logger.info("Yangi hisobot #%s, hodim id=%s", report.id, data["user_id"])

    await callback.message.edit_text(t(lang, "report_submitted"))
    await notify_partners(bot, report_full, lang)
    await callback.message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

    await state.clear()
    await callback.answer()
