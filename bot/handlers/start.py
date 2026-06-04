from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import SUPERADMIN_ID
from database.session import AsyncSessionLocal
from database.crud import (
    get_user_by_telegram_id, create_user, set_user_districts,
    get_all_districts, verify_access_password
)
from database.models import UserRole
from keyboards.employee_kb import (
    language_kb, main_menu_kb, remove_kb, districts_kb
)
from keyboards.admin_kb import admin_login_choice_kb, admin_main_menu_kb
from locales import t
from states.registration import RegistrationStates
from utils.notifications import notify_superadmin
from utils.formatters import format_user_districts

router = Router()

# Parol xato urinishlar: {telegram_id: count}
failed_attempts: dict[int, int] = {}
blocked_users: set[int] = set()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    telegram_id = message.from_user.id

    if telegram_id in blocked_users:
        await message.answer("⛔ Siz bloklandingiz. Admin bilan bog'laning.")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)

    if user and not user.is_active:
        await message.answer("⛔ Hisobingiz bloklangan. Admin bilan bog'laning.")
        return

    if user:
        lang = user.language
        is_admin = user.role in (UserRole.admin, UserRole.superadmin)
        if is_admin:
            await message.answer(
                t(lang, "admin_login_choice"),
                reply_markup=admin_login_choice_kb(lang),
            )
        else:
            await message.answer(
                t(lang, "main_menu"),
                reply_markup=main_menu_kb(lang),
            )
        return

    # SuperAdmin birinchi marta kirsa
    if telegram_id == SUPERADMIN_ID:
        await state.set_state(RegistrationStates.waiting_language)
        await state.update_data(is_superadmin=True)
        await message.answer(
            "👋 Xush kelibsiz, Salohiddin!\n\n" + t("uz", "choose_language"),
            reply_markup=language_kb(),
        )
        return

    await message.answer(t("uz", "choose_language"), reply_markup=language_kb())
    await state.set_state(RegistrationStates.waiting_language)


@router.callback_query(RegistrationStates.waiting_language, F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    data = await state.get_data()
    is_superadmin = data.get("is_superadmin", False)
    await state.update_data(language=lang)

    if is_superadmin:
        await callback.message.edit_text(t(lang, "enter_full_name"))
        await state.set_state(RegistrationStates.waiting_full_name)
    else:
        await callback.message.edit_text(t(lang, "enter_password"))
        await state.set_state(RegistrationStates.waiting_password)
    await callback.answer()


@router.message(RegistrationStates.waiting_password)
async def check_password(message: Message, state: FSMContext, bot: Bot):
    telegram_id = message.from_user.id
    data = await state.get_data()
    lang = data.get("language", "uz")
    raw_password = message.text.strip()

    async with AsyncSessionLocal() as session:
        is_valid = await verify_access_password(session, raw_password)

    if not is_valid:
        failed_attempts[telegram_id] = failed_attempts.get(telegram_id, 0) + 1
        attempts = failed_attempts[telegram_id]
        if attempts >= 3:
            blocked_users.add(telegram_id)
            await message.answer(t(lang, "account_blocked"))
            await state.clear()
            return
        await message.answer(t(lang, "wrong_password", attempts=attempts))
        return

    failed_attempts.pop(telegram_id, None)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)

    if user:
        lang = user.language
        is_admin = user.role in (UserRole.admin, UserRole.superadmin)
        if is_admin:
            await message.answer(
                t(lang, "admin_login_choice"),
                reply_markup=admin_login_choice_kb(lang),
            )
        else:
            await message.answer(
                t(lang, "main_menu"),
                reply_markup=main_menu_kb(lang),
            )
        await state.clear()
        return

    await message.answer(t(lang, "enter_full_name"), reply_markup=remove_kb())
    await state.set_state(RegistrationStates.waiting_full_name)


@router.message(RegistrationStates.waiting_full_name)
async def enter_full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(full_name=message.text.strip())
    await message.answer(t(lang, "enter_position"))
    await state.set_state(RegistrationStates.waiting_position)


@router.message(RegistrationStates.waiting_position)
async def enter_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(position=message.text.strip())

    async with AsyncSessionLocal() as session:
        all_districts = await get_all_districts(session)

    await state.update_data(selected_district_ids=[])
    await message.answer(
        t(lang, "choose_districts"),
        reply_markup=districts_kb(lang, all_districts, []),
    )
    await state.set_state(RegistrationStates.waiting_districts)


@router.callback_query(RegistrationStates.waiting_districts, F.data.startswith("dist:"))
async def toggle_district(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("language", "uz")
    action = callback.data.split(":")[1]

    if action == "done":
        selected = data.get("selected_district_ids", [])
        if not selected:
            await callback.answer(t(lang, "no_districts_selected"), show_alert=True)
            return

        telegram_id = callback.from_user.id
        is_superadmin = data.get("is_superadmin", False)
        role = UserRole.superadmin if is_superadmin else UserRole.employee

        async with AsyncSessionLocal() as session:
            user = await create_user(
                session,
                telegram_id=telegram_id,
                full_name=data["full_name"],
                position=data["position"],
                language=lang,
                role=role,
            )
            await set_user_districts(session, user.id, selected)
            user_after = await get_user_by_telegram_id(session, telegram_id)
            districts_text = format_user_districts(user_after.user_districts, lang)

        await callback.message.edit_text(
            t(lang, "registration_complete",
              full_name=data["full_name"],
              position=data["position"],
              districts=districts_text),
        )

        if not is_superadmin:
            await notify_superadmin(
                bot, SUPERADMIN_ID,
                t("uz", "new_employee_notify",
                  full_name=data["full_name"],
                  position=data["position"],
                  districts=districts_text),
            )

        if is_superadmin:
            async with AsyncSessionLocal() as session:
                u = await get_user_by_telegram_id(session, telegram_id)
            await callback.message.answer(
                t(lang, "admin_menu"),
                reply_markup=admin_main_menu_kb(lang, is_superadmin=True),
            )
        else:
            await callback.message.answer(
                t(lang, "main_menu"),
                reply_markup=main_menu_kb(lang),
            )

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


@router.callback_query(F.data.startswith("admin_login:"))
async def admin_login_choice_handler(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)

    if not user:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    lang = user.language
    is_superadmin = user.role == UserRole.superadmin

    if choice == "employee":
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            t(lang, "main_menu"),
            reply_markup=main_menu_kb(lang),
        )
    else:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            t(lang, "admin_menu"),
            reply_markup=admin_main_menu_kb(lang, is_superadmin),
        )

    await callback.answer()
