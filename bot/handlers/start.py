import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
from database.crud import (
    create_user,
    get_all_districts,
    get_unlinked_users,
    get_user_by_id,
    is_access_blocked,
    link_telegram_account,
    register_failed_attempt,
    reset_access_attempts,
    set_user_districts,
    verify_access_password,
)
from database.models import User, UserRole
from database.session import AsyncSessionLocal
from keyboards.admin_kb import admin_login_choice_kb, admin_main_menu_kb
from keyboards.employee_kb import (
    districts_kb,
    language_kb,
    link_accounts_kb,
    main_menu_kb,
    remove_kb,
)
from locales import t
from states.registration import RegistrationStates
from utils.formatters import format_user_districts
from utils.messages import text_of
from utils.notifications import notify_superadmin

logger = logging.getLogger(__name__)
router = Router()


async def show_home(message: Message, user: User) -> None:
    """Foydalanuvchi roliga mos boshlang'ich menyuni ko'rsatadi."""
    lang = user.language
    if user.role in (UserRole.admin, UserRole.superadmin):
        await message.answer(
            t(lang, "admin_login_choice"),
            reply_markup=admin_login_choice_kb(lang),
        )
    else:
        await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, db_user: User | None = None
):
    await state.clear()
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        if await is_access_blocked(session, telegram_id):
            await message.answer(t("uz", "account_blocked"))
            return

    if db_user and not db_user.is_active:
        await message.answer(t(db_user.language, "account_deactivated"))
        return

    if db_user:
        await show_home(message, db_user)
        return

    if telegram_id == config.SUPERADMIN_ID:
        await state.update_data(is_superadmin=True)

    await message.answer(t("uz", "choose_language"), reply_markup=language_kb())
    await state.set_state(RegistrationStates.waiting_language)


# Bekor qilish state li handlerlardan oldin turishi shart, aks holda
# /cancel oddiy matn sifatida qabul qilinadi.
@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message, state: FSMContext, db_user: User | None = None
):
    lang = db_user.language if db_user else "uz"
    had_state = await state.get_state() is not None
    await state.clear()

    await message.answer(
        t(lang, "action_cancelled" if had_state else "nothing_to_cancel"),
        reply_markup=remove_kb(),
    )
    if db_user and db_user.is_active:
        await show_home(message, db_user)


@router.callback_query(RegistrationStates.waiting_language, F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    data = await state.get_data()
    await state.update_data(language=lang)

    if data.get("is_superadmin", False):
        await callback.message.edit_text(t(lang, "enter_full_name"))
        await state.set_state(RegistrationStates.waiting_full_name)
    else:
        await callback.message.edit_text(t(lang, "enter_password"))
        await state.set_state(RegistrationStates.waiting_password)
    await callback.answer()


@router.message(RegistrationStates.waiting_password)
async def check_password(
    message: Message, state: FSMContext, db_user: User | None = None
):
    telegram_id = message.from_user.id
    data = await state.get_data()
    lang = data.get("language", "uz")

    raw_password = text_of(message)
    if raw_password is None:
        await message.answer(t(lang, "text_expected"))
        return

    async with AsyncSessionLocal() as session:
        if not await verify_access_password(session, raw_password):
            attempts, blocked = await register_failed_attempt(
                session, telegram_id, config.MAX_PASSWORD_ATTEMPTS
            )
            if blocked:
                logger.warning(
                    "Parol %s marta xato kiritildi, bloklandi: %s",
                    attempts, telegram_id,
                )
                await message.answer(t(lang, "account_blocked"))
                await state.clear()
            else:
                await message.answer(t(lang, "wrong_password", attempts=attempts))
            return

        await reset_access_attempts(session, telegram_id)
        unlinked = await get_unlinked_users(session)

    if db_user:
        await state.clear()
        await show_home(message, db_user)
        return

    if unlinked:
        # Admin bu hodimni oldindan kiritgan bo'lishi mumkin — takror yozuv
        # yaratilmasligi uchun o'zini ro'yxatdan tanlashni taklif qilamiz.
        await message.answer(
            t(lang, "choose_your_record"),
            reply_markup=link_accounts_kb(lang, unlinked),
        )
        await state.set_state(RegistrationStates.waiting_link_choice)
        return

    await message.answer(t(lang, "enter_full_name"), reply_markup=remove_kb())
    await state.set_state(RegistrationStates.waiting_full_name)


@router.callback_query(
    RegistrationStates.waiting_link_choice, F.data.startswith("link:")
)
async def choose_existing_record(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")
    action = callback.data.split(":")[1]

    if action == "new":
        await callback.message.edit_text(t(lang, "enter_full_name"))
        await state.set_state(RegistrationStates.waiting_full_name)
        await callback.answer()
        return

    async with AsyncSessionLocal() as session:
        user = await link_telegram_account(
            session, int(action), callback.from_user.id, lang
        )
        if user is None:
            await callback.answer(t(lang, "record_already_taken"), show_alert=True)
            return
        user = await get_user_by_id(session, user.id)
        districts_text = format_user_districts(user.user_districts, lang)

    await callback.message.edit_text(
        t(lang, "registration_complete",
          full_name=user.full_name,
          position=user.position,
          districts=districts_text)
    )
    await callback.message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))
    await state.clear()
    await callback.answer()


@router.message(RegistrationStates.waiting_full_name)
async def enter_full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")

    full_name = text_of(message)
    if not full_name:
        await message.answer(t(lang, "text_expected"))
        return

    await state.update_data(full_name=full_name)
    await message.answer(t(lang, "enter_position"))
    await state.set_state(RegistrationStates.waiting_position)


@router.message(RegistrationStates.waiting_position)
async def enter_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")

    position = text_of(message)
    if not position:
        await message.answer(t(lang, "text_expected"))
        return

    await state.update_data(position=position, selected_district_ids=[])

    async with AsyncSessionLocal() as session:
        all_districts = await get_all_districts(session)

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

    if action != "done":
        selected = data.get("selected_district_ids", [])
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

    selected = data.get("selected_district_ids", [])
    if not selected:
        await callback.answer(t(lang, "no_districts_selected"), show_alert=True)
        return

    is_superadmin = data.get("is_superadmin", False)
    role = UserRole.superadmin if is_superadmin else UserRole.employee

    async with AsyncSessionLocal() as session:
        user = await create_user(
            session,
            telegram_id=callback.from_user.id,
            full_name=data["full_name"],
            position=data["position"],
            language=lang,
            role=role,
        )
        await set_user_districts(session, user.id, selected)
        user = await get_user_by_id(session, user.id)
        districts_text = format_user_districts(user.user_districts, lang)

    await callback.message.edit_text(
        t(lang, "registration_complete",
          full_name=user.full_name,
          position=user.position,
          districts=districts_text),
    )

    if is_superadmin:
        await callback.message.answer(
            t(lang, "admin_menu"),
            reply_markup=admin_main_menu_kb(lang, is_superadmin=True),
        )
    else:
        await notify_superadmin(
            bot, config.SUPERADMIN_ID,
            t("uz", "new_employee_notify",
              full_name=user.full_name,
              position=user.position,
              districts=districts_text),
        )
        await callback.message.answer(
            t(lang, "main_menu"), reply_markup=main_menu_kb(lang)
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("admin_login:"))
async def admin_login_choice_handler(
    callback: CallbackQuery, state: FSMContext, db_user: User | None = None
):
    if not db_user or db_user.role not in (UserRole.admin, UserRole.superadmin):
        await callback.answer(t("uz", "not_authorized"), show_alert=True)
        return

    lang = db_user.language
    choice = callback.data.split(":")[1]

    await callback.message.edit_reply_markup(reply_markup=None)
    if choice == "employee":
        await callback.message.answer(
            t(lang, "main_menu"), reply_markup=main_menu_kb(lang)
        )
    else:
        await callback.message.answer(
            t(lang, "admin_menu"),
            reply_markup=admin_main_menu_kb(
                lang, db_user.role == UserRole.superadmin
            ),
        )
    await callback.answer()
