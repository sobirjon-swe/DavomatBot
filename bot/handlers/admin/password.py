import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import config
from database.crud import change_access_password, verify_access_password
from database.models import User
from database.session import AsyncSessionLocal
from filters.roles import IsAdmin
from locales import t
from states.admin import AdminPasswordStates
from utils.messages import text_of

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text.in_(["🔑 Parolni o'zgartirish", "🔑 Изменить пароль"]))
async def change_password_start(
    message: Message, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language
    await state.update_data(lang=lang, admin_id=db_user.id)
    await message.answer(t(lang, "enter_current_password"))
    await state.set_state(AdminPasswordStates.entering_current)


@router.message(AdminPasswordStates.entering_current)
async def verify_current_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    current = text_of(message)
    if current is None:
        await message.answer(t(lang, "text_expected"))
        return

    async with AsyncSessionLocal() as session:
        if not await verify_access_password(session, current):
            await message.answer(t(lang, "wrong_current_password"))
            await state.clear()
            return

    await message.answer(
        t(lang, "enter_new_password", min=config.MIN_PASSWORD_LENGTH)
    )
    await state.set_state(AdminPasswordStates.entering_new)


@router.message(AdminPasswordStates.entering_new)
async def enter_new_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    new_password = text_of(message)
    if new_password is None:
        await message.answer(t(lang, "text_expected"))
        return
    if len(new_password) < config.MIN_PASSWORD_LENGTH:
        await message.answer(
            t(lang, "password_too_short", min=config.MIN_PASSWORD_LENGTH)
        )
        return

    await state.update_data(new_password=new_password)
    await message.answer(t(lang, "enter_confirm_password"))
    await state.set_state(AdminPasswordStates.entering_confirm)


@router.message(AdminPasswordStates.entering_confirm)
async def confirm_new_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    new_password = data.get("new_password")

    if text_of(message) != new_password:
        await message.answer(t(lang, "passwords_mismatch"))
        await state.clear()
        return

    admin_id = data.get("admin_id")
    async with AsyncSessionLocal() as session:
        await change_access_password(session, new_password, admin_id)

    logger.info("Kirish paroli o'zgartirildi, admin id=%s", admin_id)
    await message.answer(t(lang, "password_changed"))
    await state.clear()
