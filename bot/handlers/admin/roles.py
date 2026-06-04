from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_all_users, get_user_by_id, update_user
)
from database.models import UserRole
from keyboards.admin_kb import employees_list_kb, role_choice_kb
from locales import t
from states.admin import AdminRoleStates

router = Router()


@router.message(F.text.in_(["👑 Rolni o'zgartirish", "👑 Изменить роли"]))
async def roles_menu(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user or user.role != UserRole.superadmin:
        await message.answer(t(user.language if user else "uz", "not_authorized"))
        return

    lang = user.language
    async with AsyncSessionLocal() as session:
        all_users = await get_all_users(session)

    non_superadmins = [u for u in all_users if u.role != UserRole.superadmin]
    await state.update_data(lang=lang)
    await message.answer(
        t(lang, "choose_employee_for_role"),
        reply_markup=employees_list_kb(lang, non_superadmins),
    )
    await state.set_state(AdminRoleStates.choosing_employee)


@router.callback_query(AdminRoleStates.choosing_employee, F.data.startswith("sel_emp:"))
async def choose_employee_for_role(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    lang = data.get("lang", "uz")

    async with AsyncSessionLocal() as session:
        target = await get_user_by_id(session, user_id)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    await state.update_data(target_user_id=user_id)
    await callback.message.edit_text(
        t(lang, "choose_new_role",
          full_name=target.full_name,
          current_role=target.role.value),
        reply_markup=role_choice_kb(lang, target.role.value),
    )
    await state.set_state(AdminRoleStates.choosing_role)
    await callback.answer()


@router.callback_query(AdminRoleStates.choosing_role, F.data.startswith("role:"))
async def choose_new_role(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    action = callback.data.split(":")[1]

    if action == "cancel":
        await callback.message.edit_text(t(lang, "btn_cancel"))
        await state.clear()
        await callback.answer()
        return

    target_user_id = data.get("target_user_id")
    new_role = UserRole.admin if action == "admin" else UserRole.employee

    async with AsyncSessionLocal() as session:
        target = await update_user(session, target_user_id, role=new_role)

    if not target:
        await callback.answer(t(lang, "employee_not_found"), show_alert=True)
        return

    notify_text = t(lang, "admin_assigned_notify") if new_role == UserRole.admin else t(lang, "admin_removed_notify")
    try:
        await bot.send_message(chat_id=target.telegram_id, text=notify_text)
    except Exception:
        pass

    await callback.message.edit_text(
        t(lang, "role_updated",
          full_name=target.full_name,
          new_role=new_role.value)
    )
    await state.clear()
    await callback.answer()
