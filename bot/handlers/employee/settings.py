from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, get_all_districts, set_user_districts,
    update_user
)
from keyboards.employee_kb import settings_kb, districts_kb, language_kb, main_menu_kb
from locales import t
from states.settings import SettingsStates
from utils.formatters import format_user_districts

router = Router()


@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки"]))
async def settings_menu(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        return

    lang = user.language
    await message.answer(t(lang, "settings_menu"), reply_markup=settings_kb(lang))


@router.callback_query(F.data == "settings:districts")
async def edit_districts_start(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        all_districts = await get_all_districts(session)
        selected_ids = [ud.district_id for ud in user.user_districts]

    lang = user.language
    await state.update_data(selected_district_ids=selected_ids)
    await callback.message.edit_text(
        t(lang, "choose_districts"),
        reply_markup=districts_kb(lang, all_districts, selected_ids),
    )
    await state.set_state(SettingsStates.editing_districts)
    await callback.answer()


@router.callback_query(SettingsStates.editing_districts, F.data.startswith("dist:"))
async def toggle_district_settings(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    action = callback.data.split(":")[1]

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
    lang = user.language

    if action == "done":
        selected = data.get("selected_district_ids", [])
        if not selected:
            await callback.answer(t(lang, "no_districts_selected"), show_alert=True)
            return

        async with AsyncSessionLocal() as session:
            await set_user_districts(session, user.id, selected)

        await callback.message.edit_text(t(lang, "districts_updated"))
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


@router.callback_query(F.data == "settings:language")
async def change_language_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        t("uz", "choose_language"),
        reply_markup=language_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def change_language(callback: CallbackQuery, state: FSMContext):
    fsm_state = await state.get_state()
    if fsm_state is not None:
        return

    lang = callback.data.split(":")[1]
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            return
        await update_user(session, user.id, language=lang)

    await callback.message.edit_text(t(lang, "language_changed"))
    await callback.message.answer(
        t(lang, "main_menu"),
        reply_markup=main_menu_kb(lang),
    )
    await callback.answer()
