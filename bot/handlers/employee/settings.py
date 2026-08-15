from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.crud import (
    get_all_districts, get_user_district_ids, set_user_districts, update_user
)
from database.models import User
from database.session import AsyncSessionLocal
from keyboards.employee_kb import districts_kb, language_kb, main_menu_kb, settings_kb
from locales import t
from states.settings import SettingsStates

router = Router()


@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки"]))
async def settings_menu(
    message: Message, state: FSMContext, db_user: Optional[User] = None
):
    if not db_user or not db_user.is_active:
        return
    await message.answer(
        t(db_user.language, "settings_menu"),
        reply_markup=settings_kb(db_user.language),
    )


@router.callback_query(F.data == "settings:districts")
async def edit_districts_start(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    if not db_user:
        await callback.answer(t("uz", "not_authorized"), show_alert=True)
        return

    lang = db_user.language
    async with AsyncSessionLocal() as session:
        all_districts = await get_all_districts(session)
        selected_ids = await get_user_district_ids(session, db_user.id)

    await state.update_data(selected_district_ids=selected_ids, user_id=db_user.id)
    await callback.message.edit_text(
        t(lang, "choose_districts"),
        reply_markup=districts_kb(lang, all_districts, selected_ids),
    )
    await state.set_state(SettingsStates.editing_districts)
    await callback.answer()


@router.callback_query(SettingsStates.editing_districts, F.data.startswith("dist:"))
async def toggle_district_settings(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    if not db_user:
        await callback.answer(t("uz", "not_authorized"), show_alert=True)
        return

    lang = db_user.language
    data = await state.get_data()
    action = callback.data.split(":")[1]
    selected = data.get("selected_district_ids", [])

    if action == "done":
        if not selected:
            await callback.answer(t(lang, "no_districts_selected"), show_alert=True)
            return

        async with AsyncSessionLocal() as session:
            await set_user_districts(session, db_user.id, selected)

        await callback.message.edit_text(t(lang, "districts_updated"))
        await state.clear()
        await callback.answer()
        return

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


@router.callback_query(F.data == "settings:language")
async def change_language_start(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    if not db_user:
        await callback.answer(t("uz", "not_authorized"), show_alert=True)
        return

    await callback.message.edit_text(
        t(db_user.language, "choose_language"), reply_markup=language_kb()
    )
    # Holat qo'yiladi, aks holda bu handler ro'yxatdan o'tish oqimidagi
    # "lang:" tugmalari bilan to'qnashadi.
    await state.set_state(SettingsStates.editing_language)
    await callback.answer()


@router.callback_query(SettingsStates.editing_language, F.data.startswith("lang:"))
async def change_language(
    callback: CallbackQuery, state: FSMContext, db_user: Optional[User] = None
):
    if not db_user:
        await callback.answer(t("uz", "not_authorized"), show_alert=True)
        return

    lang = callback.data.split(":")[1]
    async with AsyncSessionLocal() as session:
        await update_user(session, db_user.id, language=lang)

    await callback.message.edit_text(t(lang, "language_changed"))
    await callback.message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))
    await state.clear()
    await callback.answer()
