import asyncio
from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message

import config
from database.crud import (
    count_reports_by_date_and_user,
    count_today_reports,
    get_all_users,
    get_employees_without_report,
    get_report_by_id,
    get_reports_by_date_and_user,
    get_today_reports,
    list_reports,
    local_today,
)
from database.models import User, UserRole
from database.session import AsyncSessionLocal
from filters.roles import IsAdmin
from keyboards.admin_kb import (
    employees_list_kb,
    export_range_kb,
    reports_section_kb,
    view_photos_kb,
)
from keyboards.pagination import (
    PER_PAGE,
    clamp,
    list_page_kb,
    offset_of,
    page_count,
    with_back_button,
)
from locales import t
from states.admin import AdminExportStates, AdminReportStates
from utils.export import build_workbook, file_name
from utils.formatters import build_report_caption, esc, format_datetime
from utils.menu_texts import RESERVED_MENU_TEXTS
from utils.messages import text_of
from utils.reminders import format_missing

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _load_page(state: FSMContext, page: int):
    """Joriy ro'yxat kontekstiga qarab bitta sahifani o'qiydi.

    Kontekst FSM da saqlanadi: "bugungi" yoki sana+hodim bo'yicha qidiruv.
    Callback ma'lumotiga sig'dirish o'rniga shunday qilingan — callback_data
    64 bayt bilan cheklangan.
    """
    data = await state.get_data()
    rlist = data.get("rlist") or {"mode": "today"}

    async with AsyncSessionLocal() as session:
        if rlist["mode"] == "search":
            search_date = date.fromisoformat(rlist["date"])
            user_id = rlist["user_id"]
            total = await count_reports_by_date_and_user(session, search_date, user_id)
            pages = page_count(total)
            page = clamp(page, pages)
            reports = await get_reports_by_date_and_user(
                session, search_date, user_id,
                offset=offset_of(page), limit=PER_PAGE,
            )
        else:
            total = await count_today_reports(session)
            pages = page_count(total)
            page = clamp(page, pages)
            reports = await get_today_reports(
                session, offset=offset_of(page), limit=PER_PAGE
            )

    return reports, total, page, pages


async def _show_reports_page(
    callback: CallbackQuery, state: FSMContext, lang: str, page: int
) -> None:
    reports, total, page, pages = await _load_page(state, page)

    if not reports:
        await callback.message.edit_text(t(lang, "no_reports"))
        return

    lines = [t(lang, "reports_list_header", total=total), ""]
    for report in reports:
        lines.append(
            f"• <b>{esc(report.user.full_name)}</b> — {esc(report.customer_name)}\n"
            f"  {format_datetime(report.created_at)}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=list_page_kb(
            open_prefix="rpt_card",
            page_prefix="rpt_page",
            page=page,
            pages=pages,
            items=[(r.id, f"{r.user.full_name} — {r.customer_name}"[:60]) for r in reports],
        ),
    )


@router.message(F.text.in_(["📊 Hisobotlar", "📊 Отчёты"]))
async def reports_menu(
    message: Message, state: FSMContext, db_user: User | None = None
):
    await state.clear()
    await message.answer(
        t(db_user.language, "reports_menu"),
        reply_markup=reports_section_kb(db_user.language),
    )


@router.callback_query(F.data == "rpt:today")
async def today_reports(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    await state.set_state(None)
    await state.update_data(rlist={"mode": "today"})
    await _show_reports_page(callback, state, db_user.language, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("rpt_page:"))
async def reports_page(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    page = int(callback.data.split(":")[1])
    await _show_reports_page(callback, state, db_user.language, page)
    await callback.answer()


@router.callback_query(F.data.startswith("rpt_card:"))
async def report_card(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    _, raw_id, raw_page = callback.data.split(":")

    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, int(raw_id))

    if not report:
        await callback.answer(t(lang, "report_not_found"), show_alert=True)
        return

    await callback.message.edit_text(
        build_report_caption(lang, report),
        parse_mode="HTML",
        reply_markup=with_back_button(
            lang,
            "rpt_page",
            int(raw_page),
            view_photos_kb(lang, report.id) if report.photos else None,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "rpt:missing")
async def missing_reports(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    """Bugun hisobot bermagan hodimlar — kunlik yakunning talab bo'yicha varianti."""
    lang = db_user.language
    today = local_today()

    async with AsyncSessionLocal() as session:
        employees = await get_employees_without_report(
            session, today, only_role=UserRole.employee
        )

    await callback.message.edit_text(
        format_missing(lang, today, employees), parse_mode="HTML"
    )
    await callback.answer()


# ─── Excel eksport ──────────────────────────────────────────────────────────

def parse_range(raw: str, today: date) -> tuple[date, date] | None:
    """"01.06.2026 - 30.06.2026" yoki bitta sanani o'qiydi.

    Sanalar teskari yozilgan bo'lsa o'rin almashtiriladi — foydalanuvchini
    xato bilan qaytarishdan ko'ra shu ma'qul.
    """
    parts = [part.strip() for part in raw.replace("—", "-").split("-") if part.strip()]
    if not parts or len(parts) > 2:
        return None

    try:
        dates = [datetime.strptime(part, "%d.%m.%Y").date() for part in parts]
    except ValueError:
        return None

    start, end = (dates[0], dates[-1])
    if start > end:
        start, end = end, start
    return start, end


def format_range(date_from: date, date_to: date) -> str:
    if date_from == date_to:
        return date_from.strftime("%d.%m.%Y")
    return f"{date_from:%d.%m.%Y} - {date_to:%d.%m.%Y}"


async def _send_export(message: Message, lang: str, date_from: date, date_to: date) -> None:
    label = format_range(date_from, date_to)

    async with AsyncSessionLocal() as session:
        reports = await list_reports(session, date_from=date_from, date_to=date_to)

    if not reports:
        await message.answer(t(lang, "export_empty", range=label))
        return

    status = await message.answer(t(lang, "export_preparing"))

    # openpyxl sinxron ishlaydi; katta oraliqda event loop qotib
    # qolmasligi uchun alohida oqimga chiqariladi.
    payload = await asyncio.to_thread(build_workbook, lang, reports)

    await message.answer_document(
        BufferedInputFile(payload, filename=file_name(date_from, date_to)),
        caption=t(lang, "export_caption", range=label, count=len(reports)),
    )
    await status.delete()


@router.callback_query(F.data == "rpt:export")
async def export_start(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    await state.update_data(lang=lang)
    await callback.message.edit_text(
        t(lang, "export_choose_range"), reply_markup=export_range_kb(lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exp:"))
async def export_range(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    choice = callback.data.split(":")[1]
    today = local_today()

    if choice == "custom":
        await callback.message.edit_text(t(lang, "export_enter_range"), parse_mode="HTML")
        await state.set_state(AdminExportStates.entering_range)
        await callback.answer()
        return

    if choice == "today":
        date_from = date_to = today
    elif choice == "week":
        date_from, date_to = today - timedelta(days=today.weekday()), today
    else:
        date_from, date_to = today.replace(day=1), today

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await _send_export(callback.message, lang, date_from, date_to)


@router.message(AdminExportStates.entering_range, ~F.text.in_(RESERVED_MENU_TEXTS))
async def export_custom_range(
    message: Message, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language

    raw = text_of(message)
    if raw is None:
        await message.answer(t(lang, "text_expected"))
        return

    parsed = parse_range(raw, local_today())
    if parsed is None:
        await message.answer(t(lang, "export_invalid_range"))
        return

    date_from, date_to = parsed
    if (date_to - date_from).days + 1 > config.MAX_EXPORT_DAYS:
        await message.answer(
            t(lang, "export_range_too_long", max=config.MAX_EXPORT_DAYS)
        )
        return

    await state.clear()
    await _send_export(message, lang, date_from, date_to)


# ─── Qidiruv ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "rpt:search")
async def search_reports_start(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "search_date"))
    await state.set_state(AdminReportStates.entering_date)
    await callback.answer()


@router.message(AdminReportStates.entering_date, ~F.text.in_(RESERVED_MENU_TEXTS))
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
        employees = await get_all_users(session, only_active=True)

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
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    data = await state.get_data()
    user_id = int(callback.data.split(":")[1])

    # Holat tozalanmaydi: sahifalar bo'ylab yurish uchun kontekst kerak.
    await state.set_state(None)
    await state.update_data(
        rlist={"mode": "search", "date": data["search_date"], "user_id": user_id}
    )
    await _show_reports_page(callback, state, db_user.language, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("rpt_photos:"))
async def view_report_photos(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
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
