import logging
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.crud import get_all_users, get_user_by_id, update_user
from database.models import User, UserRole
from database.session import AsyncSessionLocal
from filters.roles import IsSuperAdmin
from keyboards.admin_kb import employees_list_kb, role_choice_kb
from locales import t
from states.admin import AdminRoleStates
from utils.notifications import notify_user

logger = logging.getLogger(__name__)

router = Router()
# Rol berish faqat superadminga — callback tugmalari ham shu filtr ostida.
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


@router.message(F.text.in_(["👑 Rolni o'zgartirish", "👑 Изменить роли"]))
async def roles_menu(
    message: Message, state: FSMContext, db_user: Optional[User] = None
):
    lang = db_user.language

    async with AsyncSessionLocal() as session:
        all_users = await get_all_users(session)

    candidates = [u for u in all_users if u.role != UserRole.superadmin]
    if not candidates:
        await message.answer(t(lang, "no_employees"))
        return

    await state.update_data(lang=lang)
    await message.answer(
        t(lang, "choose_employee_for_role"),
        reply_markup=employees_list_kb(lang, candidates),
    )
    await state.set_state(AdminRoleStates.choosing_employee)


@router.callback_query(AdminRoleStates.choosing_employee, F.data.startswith("sel_emp:"))
async def choose_employee_for_role(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    user_id = int(callback.data.split(":")[1])

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

    logger.info("Hodim id=%s roli %s ga o'zgartirildi", target.id, new_role.value)

    if target.telegram_id is not None:
        await notify_user(
            bot, target.telegram_id,
            t(target.language,
              "admin_assigned_notify" if new_role == UserRole.admin
              else "admin_removed_notify"),
        )

    await callback.message.edit_text(
        t(lang, "role_updated", full_name=target.full_name, new_role=new_role.value)
    )
    await state.clear()
    await callback.answer()
