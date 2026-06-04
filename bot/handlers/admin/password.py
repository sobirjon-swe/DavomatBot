from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, verify_access_password, change_access_password
)
from database.models import UserRole
from locales import t
from states.admin import AdminPasswordStates

router = Router()


@router.message(F.text.in_(["🔑 Parolni o'zgartirish", "🔑 Изменить пароль"]))
async def change_password_start(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user or user.role not in (UserRole.admin, UserRole.superadmin):
        return

    lang = user.language
    await state.update_data(lang=lang, admin_id=user.id)
    await message.answer(t(lang, "enter_current_password"))
    await state.set_state(AdminPasswordStates.entering_current)


@router.message(AdminPasswordStates.entering_current)
async def verify_current_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    async with AsyncSessionLocal() as session:
        is_valid = await verify_access_password(session, message.text.strip())

    if not is_valid:
        await message.answer(t(lang, "wrong_current_password"))
        await state.clear()
        return

    await message.answer(t(lang, "enter_new_password"))
    await state.set_state(AdminPasswordStates.entering_new)


@router.message(AdminPasswordStates.entering_new)
async def enter_new_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(new_password=message.text.strip())
    await message.answer(t(lang, "enter_confirm_password"))
    await state.set_state(AdminPasswordStates.entering_confirm)


@router.message(AdminPasswordStates.entering_confirm)
async def confirm_new_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    new_password = data.get("new_password")

    if message.text.strip() != new_password:
        await message.answer(t(lang, "passwords_mismatch"))
        await state.clear()
        return

    admin_id = data.get("admin_id")
    async with AsyncSessionLocal() as session:
        await change_access_password(session, new_password, admin_id)

    await message.answer(t(lang, "password_changed"))
    await state.clear()
