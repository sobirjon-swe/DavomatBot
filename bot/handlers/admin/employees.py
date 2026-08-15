import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.crud import (
    count_users,
    create_user,
    get_all_districts,
    get_all_users,
    get_user_by_id,
    set_user_active,
    set_user_districts,
    update_user,
)
from database.models import User, UserRole
from database.session import AsyncSessionLocal
from filters.roles import IsAdmin
from keyboards.admin_kb import (
    confirm_deactivate_kb,
    edit_employee_menu_kb,
    employee_actions_kb,
    employees_section_kb,
)
from keyboards.employee_kb import districts_kb
from keyboards.pagination import (
    PER_PAGE,
    clamp,
    list_page_kb,
    offset_of,
    page_count,
    with_back_button,
)
from locales import t
from states.admin import AdminEmployeeStates
from utils.formatters import esc, format_role, format_user_districts
from utils.messages import text_of

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text.in_(["👥 Hodimlar", "👥 Сотрудники"]))
async def employees_menu(
    message: Message, state: FSMContext, db_user: User | None = None
):
    await message.answer(
        t(db_user.language, "employees_menu"),
        reply_markup=employees_section_kb(db_user.language),
    )


def _employee_card(lang: str, user: User) -> str:
    return t(
        lang, "employee_card",
        full_name=esc(user.full_name),
        position=esc(user.position),
        role=format_role(lang, user.role.value),
        districts=format_user_districts(user.user_districts, lang),
        created_at=user.created_at.strftime("%d.%m.%Y"),
        status=t(lang, "status_active" if user.is_active else "status_inactive"),
    )


async def _show_employees_page(callback: CallbackQuery, lang: str, page: int) -> None:
    """Bitta xabarda bitta sahifa ko'rsatadi.

    Ilgari har bir hodim alohida xabar bilan yuborilardi — hodimlar soni
    o'sganda bu Telegram cheklovlariga urilardi.
    """
    async with AsyncSessionLocal() as session:
        total = await count_users(session)
        pages = page_count(total)
        page = clamp(page, pages)
        users = await get_all_users(session, offset=offset_of(page), limit=PER_PAGE)

    if not users:
        await callback.message.edit_text(t(lang, "no_employees"))
        return

    lines = [t(lang, "employees_list_header", total=total), ""]
    for user in users:
        holat = "" if user.is_active else f" ({t(lang, 'status_inactive')})"
        lines.append(f"• <b>{esc(user.full_name)}</b> — {esc(user.position)}{holat}")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=list_page_kb(
            open_prefix="emp_card",
            page_prefix="emp_page",
            page=page,
            pages=pages,
            items=[(u.id, u.full_name) for u in users],
        ),
    )


@router.callback_query(F.data == "emp:list")
async def list_employees(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    await _show_employees_page(callback, db_user.language, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("emp_page:"))
async def employees_page(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    await _show_employees_page(callback, db_user.language, int(callback.data.split(":")[1]))
    await callback.answer()


@router.callback_query(F.data.startswith("emp_card:"))
async def employee_card(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    _, raw_id, raw_page = callback.data.split(":")

    async with AsyncSessionLocal() as session:
        user = await get_user_by_id(session, int(raw_id))

    if not user:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    await callback.message.edit_text(
        _employee_card(lang, user),
        parse_mode="HTML",
        reply_markup=with_back_button(
            lang,
            "emp_page",
            int(raw_page),
            employee_actions_kb(
                lang, user.id, db_user.role == UserRole.superadmin, user.is_active
            ),
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def ignore_noop(callback: CallbackQuery):
    """Sahifa raqami va o'chirilgan o'q tugmalari."""
    await callback.answer()


# ─── Faolsizlantirish / tiklash (faqat superadmin) ──────────────────────────

@router.callback_query(F.data.startswith("emp_off:"))
async def deactivate_employee_confirm(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    if db_user.role != UserRole.superadmin:
        await callback.answer(t(lang, "not_authorized"), show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    await callback.message.answer(
        t(lang, "confirm_deactivate", full_name=target.full_name),
        reply_markup=confirm_deactivate_kb(lang, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("emp_off_confirm:"))
async def deactivate_employee(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    if db_user.role != UserRole.superadmin:
        await callback.answer(t(lang, "not_authorized"), show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    if user_id == db_user.id:
        await callback.answer(t(lang, "cannot_deactivate_self"), show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        target = await set_user_active(session, user_id, False)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    logger.info("Hodim id=%s faolsizlantirildi", user_id)
    await callback.message.edit_text(t(lang, "employee_deactivated"))
    await callback.answer()


@router.callback_query(F.data.startswith("emp_on:"))
async def activate_employee(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    if db_user.role != UserRole.superadmin:
        await callback.answer(t(lang, "not_authorized"), show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        target = await set_user_active(session, user_id, True)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    logger.info("Hodim id=%s tiklandi", user_id)
    await callback.message.edit_text(t(lang, "employee_activated"))
    await callback.answer()


@router.callback_query(F.data == "emp_off_cancel")
async def deactivate_cancel(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    await callback.message.edit_text(t(db_user.language, "btn_cancel"))
    await callback.answer()


# ─── Yangi hodim qo'shish ────────────────────────────────────────────────────

@router.callback_query(F.data == "emp:add")
async def add_employee_start(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    await state.update_data(lang=lang, mode="add")
    await callback.message.edit_text(t(lang, "add_employee_name"))
    await state.set_state(AdminEmployeeStates.entering_name)
    await callback.answer()


@router.message(AdminEmployeeStates.entering_name)
async def admin_enter_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    name = text_of(message)
    if not name:
        await message.answer(t(lang, "text_expected"))
        return

    await state.update_data(new_full_name=name)
    await message.answer(t(lang, "add_employee_position"))
    await state.set_state(AdminEmployeeStates.entering_position)


@router.message(AdminEmployeeStates.entering_position)
async def admin_enter_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    position = text_of(message)
    if not position:
        await message.answer(t(lang, "text_expected"))
        return

    await state.update_data(new_position=position, selected_district_ids=[])

    async with AsyncSessionLocal() as session:
        all_districts = await get_all_districts(session)

    await message.answer(
        t(lang, "add_employee_districts"),
        reply_markup=districts_kb(lang, all_districts, []),
    )
    await state.set_state(AdminEmployeeStates.choosing_districts)


@router.callback_query(AdminEmployeeStates.choosing_districts, F.data.startswith("dist:"))
async def admin_toggle_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    action = callback.data.split(":")[1]
    selected = data.get("selected_district_ids", [])

    if action != "done":
        district_id = int(action)
        if district_id in selected:
            selected.remove(district_id)
        else:
            selected.append(district_id)
        await state.update_data(selected_district_ids=selected)

        async with AsyncSessionLocal() as session:
            all_districts = await get_all_districts(session)

        await callback.message.edit_reply_markup(
            reply_markup=districts_kb(lang, all_districts, selected)
        )
        await callback.answer()
        return

    if not selected:
        await callback.answer(t(lang, "no_districts_selected"), show_alert=True)
        return

    if data.get("mode", "add") == "add":
        async with AsyncSessionLocal() as session:
            # telegram_id ataylab None: hodim botga birinchi kirganda
            # o'z yozuvini tanlab bog'lanadi.
            user = await create_user(
                session,
                full_name=data["new_full_name"],
                position=data["new_position"],
                language="uz",
            )
            await set_user_districts(session, user.id, selected)

        logger.info("Admin yangi hodim qo'shdi: id=%s", user.id)
        await callback.message.edit_text(
            t(lang, "employee_added",
              full_name=data["new_full_name"],
              position=data["new_position"])
        )
    else:
        async with AsyncSessionLocal() as session:
            await set_user_districts(session, data["editing_user_id"], selected)
        await callback.message.edit_text(t(lang, "employee_updated"))

    await state.clear()
    await callback.answer()


# ─── Tahrirlash ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("emp_edit:"))
async def edit_employee_menu(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    user_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    await state.update_data(editing_user_id=user_id, lang=lang)
    await callback.message.answer(
        t(lang, "edit_employee_menu"),
        reply_markup=edit_employee_menu_kb(lang, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("emp_edit_field:"))
async def edit_employee_field(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    _, raw_user_id, field = callback.data.split(":")
    user_id = int(raw_user_id)

    async with AsyncSessionLocal() as session:
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    await state.update_data(editing_user_id=user_id, lang=lang, mode="edit")

    if field == "name":
        await callback.message.edit_text(t(lang, "enter_new_name"))
        await state.set_state(AdminEmployeeStates.editing_name)
    elif field == "position":
        await callback.message.edit_text(t(lang, "enter_new_position"))
        await state.set_state(AdminEmployeeStates.editing_position)
    elif field == "districts":
        async with AsyncSessionLocal() as session:
            all_districts = await get_all_districts(session)
        current_ids = [ud.district_id for ud in target.user_districts]

        await state.update_data(selected_district_ids=current_ids)
        await callback.message.edit_text(
            t(lang, "add_employee_districts"),
            reply_markup=districts_kb(lang, all_districts, current_ids),
        )
        await state.set_state(AdminEmployeeStates.choosing_districts)

    await callback.answer()


@router.message(AdminEmployeeStates.editing_name)
async def update_employee_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    name = text_of(message)
    if not name:
        await message.answer(t(lang, "text_expected"))
        return

    async with AsyncSessionLocal() as session:
        await update_user(session, data["editing_user_id"], full_name=name)

    await message.answer(t(lang, "employee_updated"))
    await state.clear()


@router.message(AdminEmployeeStates.editing_position)
async def update_employee_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    position = text_of(message)
    if not position:
        await message.answer(t(lang, "text_expected"))
        return

    async with AsyncSessionLocal() as session:
        await update_user(session, data["editing_user_id"], position=position)

    await message.answer(t(lang, "employee_updated"))
    await state.clear()
