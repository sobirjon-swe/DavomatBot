from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_all_users, get_user_by_id,
    create_user, update_user, delete_user,
    get_all_districts, set_user_districts
)
from database.models import UserRole
from keyboards.admin_kb import (
    employees_section_kb, employee_actions_kb, confirm_delete_kb,
    edit_employee_menu_kb, back_kb
)
from keyboards.employee_kb import districts_kb
from locales import t
from states.admin import AdminEmployeeStates
from utils.formatters import format_user_districts, format_role

router = Router()


@router.message(F.text.in_(["👥 Hodimlar", "👥 Сотрудники"]))
async def employees_menu(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user or user.role not in (UserRole.admin, UserRole.superadmin):
        return

    lang = user.language
    await message.answer(t(lang, "employees_menu"), reply_markup=employees_section_kb(lang))


@router.callback_query(F.data == "emp:list")
async def list_employees(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        users = await get_all_users(session)

    lang = admin.language
    is_superadmin = admin.role == UserRole.superadmin

    if not users:
        await callback.message.edit_text(t(lang, "no_employees"))
        await callback.answer()
        return

    await callback.message.edit_text(t(lang, "employees_menu"))
    for user in users:
        districts_text = format_user_districts(user.user_districts, lang)
        role_text = format_role(lang, user.role.value)
        card = t(
            lang, "employee_card",
            full_name=user.full_name,
            position=user.position,
            role=role_text,
            districts=districts_text,
            created_at=user.created_at.strftime("%d.%m.%Y"),
        )
        await callback.message.answer(
            card,
            parse_mode="HTML",
            reply_markup=employee_actions_kb(lang, user.id, is_superadmin),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("emp_edit:"))
async def edit_employee_menu(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(admin.language, "employee_not_found"), show_alert=True)
        return

    lang = admin.language
    await state.update_data(editing_user_id=user_id, lang=lang)
    await callback.message.answer(
        t(lang, "edit_employee_menu"),
        reply_markup=edit_employee_menu_kb(lang, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("emp_del:"))
async def delete_employee_confirm(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(admin.language, "employee_not_found"), show_alert=True)
        return

    lang = admin.language
    await callback.message.answer(
        t(lang, "confirm_delete", full_name=target.full_name),
        reply_markup=confirm_delete_kb(lang, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("emp_del_confirm:"))
async def delete_employee_execute(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        await delete_user(session, user_id)

    lang = admin.language
    await callback.message.edit_text(t(lang, "employee_deleted"))
    await callback.answer()


@router.callback_query(F.data == "emp_del_cancel")
async def delete_employee_cancel(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
    await callback.message.edit_text(t(admin.language, "btn_cancel"))
    await callback.answer()


@router.callback_query(F.data == "emp:add")
async def add_employee_start(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
    lang = admin.language
    await state.update_data(lang=lang, mode="add")
    await callback.message.edit_text(t(lang, "add_employee_name"))
    await state.set_state(AdminEmployeeStates.entering_name)
    await callback.answer()


@router.message(AdminEmployeeStates.entering_name)
async def admin_enter_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(new_full_name=message.text.strip())
    await message.answer(t(lang, "add_employee_position"))
    await state.set_state(AdminEmployeeStates.entering_position)


@router.message(AdminEmployeeStates.entering_position)
async def admin_enter_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(new_position=message.text.strip())

    async with AsyncSessionLocal() as session:
        all_districts = await get_all_districts(session)

    await state.update_data(selected_district_ids=[])
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

    if action == "done":
        selected = data.get("selected_district_ids", [])
        if not selected:
            await callback.answer(t(lang, "no_districts_selected"), show_alert=True)
            return

        mode = data.get("mode", "add")
        if mode == "add":
            async with AsyncSessionLocal() as session:
                user = await create_user(
                    session,
                    telegram_id=0,
                    full_name=data["new_full_name"],
                    position=data["new_position"],
                    language="uz",
                )
                await set_user_districts(session, user.id, selected)

            await callback.message.edit_text(
                t(lang, "employee_added",
                  full_name=data["new_full_name"],
                  position=data["new_position"])
            )
        else:
            editing_user_id = data.get("editing_user_id")
            async with AsyncSessionLocal() as session:
                await set_user_districts(session, editing_user_id, selected)
            await callback.message.edit_text(t(lang, "employee_updated"))

        await state.clear()
        await callback.answer()
        return

    district_id = int(action)
    selected = data.get("selected_district_ids", [])
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


@router.callback_query(F.data.startswith("emp_edit_field:"))
async def edit_employee_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    user_id = int(parts[1])
    field = parts[2]

    async with AsyncSessionLocal() as session:
        admin = await get_user_by_telegram_id(session, callback.from_user.id)
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(admin.language, "employee_not_found"), show_alert=True)
        return

    lang = admin.language
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
    user_id = data.get("editing_user_id")
    async with AsyncSessionLocal() as session:
        await update_user(session, user_id, full_name=message.text.strip())
    await message.answer(t(lang, "employee_updated"))
    await state.clear()


@router.message(AdminEmployeeStates.editing_position)
async def update_employee_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    user_id = data.get("editing_user_id")
    async with AsyncSessionLocal() as session:
        await update_user(session, user_id, position=message.text.strip())
    await message.answer(t(lang, "employee_updated"))
    await state.clear()
