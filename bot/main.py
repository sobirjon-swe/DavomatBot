import asyncio
import logging
import secrets
import string

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

import config
from database.crud import create_initial_password, get_active_password, seed_districts
from database.session import AsyncSessionLocal, close_engine
from handlers.admin.attendance import router as attendance_router
from handlers.admin.employees import router as employees_router
from handlers.admin.password import router as password_router
from handlers.admin.reports import router as admin_reports_router
from handlers.admin.roles import router as roles_router
from handlers.employee.report import router as report_router
from handlers.employee.settings import router as settings_router
from handlers.start import router as start_router
from keyboards import webapp
from middlewares.auth import AuthMiddleware
from utils.reminders import send_reminders, send_summary
from utils.scheduler import run_daily

logger = logging.getLogger(__name__)


def _generate_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_storage() -> BaseStorage:
    """FSM omborini tanlaydi.

    REDIS_URL berilgan bo'lsa Redis ishlatiladi va bot qayta ishga
    tushganda yarim to'ldirilgan hisobotlar saqlanib qoladi.
    """
    if config.REDIS_URL:
        from aiogram.fsm.storage.redis import RedisStorage

        logger.info("FSM holati Redisda saqlanadi.")
        return RedisStorage.from_url(config.REDIS_URL)

    logger.warning(
        "REDIS_URL ko'rsatilmagan — FSM holati xotirada saqlanadi. "
        "Bot qayta ishga tushsa, to'ldirilayotgan hisobotlar yo'qoladi."
    )
    return MemoryStorage()


async def on_startup(bot: Bot) -> None:
    async with AsyncSessionLocal() as session:
        added = await seed_districts(session)
        if added:
            logger.info("Bazaga %s ta yangi tuman qo'shildi.", added)

        if not await get_active_password(session):
            raw_password = config.INITIAL_ACCESS_PASSWORD or _generate_password()
            await create_initial_password(session, raw_password)
            logger.warning(
                "Kirish paroli yaratildi: %s | Uni darhol o'zgartiring: "
                "Admin panel -> Parolni o'zgartirish.",
                raw_password,
            )

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Boshlash / Начать"),
            BotCommand(command="cancel", description="Bekor qilish / Отмена"),
        ]
    )

    # Kiritish maydoni yonidagi doimiy tugma. WEBAPP_URL bo'lmasa oddiy
    # buyruqlar menyusi qo'yiladi — eski tugma osilib qolmasligi uchun.
    await bot.set_chat_menu_button(menu_button=webapp.menu_button())
    if webapp.is_enabled():
        logger.info("Mini App tugmasi yoqildi: %s", config.WEBAPP_URL)
    else:
        logger.info("WEBAPP_URL ko'rsatilmagan — Mini App tugmalari yashirildi.")

    logger.info("Bot ishga tushdi.")


def start_scheduled_jobs(bot: Bot) -> list[asyncio.Task[None]]:
    """Kunlik eslatma va yakunni fon vazifasi sifatida yoqadi.

    Vaqt ko'rsatilmagan bo'lsa vazifa umuman ishga tushmaydi.
    """
    tasks: list[asyncio.Task[None]] = []

    if config.REMINDER_TIME:
        tasks.append(
            asyncio.create_task(
                run_daily(
                    "Kunlik eslatma",
                    config.REMINDER_TIME,
                    lambda day: send_reminders(bot, day),
                )
            )
        )
        logger.info("Kunlik eslatma yoqildi: %s", config.REMINDER_TIME.strftime("%H:%M"))

    if config.SUMMARY_TIME:
        tasks.append(
            asyncio.create_task(
                run_daily(
                    "Kunlik yakun",
                    config.SUMMARY_TIME,
                    lambda day: send_summary(bot, day),
                )
            )
        )
        logger.info("Kunlik yakun yoqildi: %s", config.SUMMARY_TIME.strftime("%H:%M"))

    if not tasks:
        logger.info("REMINDER_TIME va SUMMARY_TIME ko'rsatilmagan — eslatmalar o'chiq.")

    return tasks


async def on_error(event: ErrorEvent) -> bool:
    """Ushlanmagan xatoni logga yozadi va botni to'xtab qolishdan saqlaydi."""
    logger.exception(
        "Yangilanishni ishlashda xato: %r", event.exception, exc_info=event.exception
    )

    # Callback ichida xato bo'lsa callback.answer() chaqirilmay qolgan bo'lishi
    # mumkin — mijozda tugma "aylanib" osilib qoladi, shuni tozalaymiz.
    callback = getattr(event.update, "callback_query", None)
    if callback is not None:
        try:
            await callback.answer()
        except Exception:
            pass

    return True


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    config.validate()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=build_storage())

    # Rol filtrlari ishlashi uchun db_user handlerdan oldin tayyor bo'lishi
    # kerak — shuning uchun outer middleware.
    auth = AuthMiddleware()
    dp.message.outer_middleware(auth)
    dp.callback_query.outer_middleware(auth)

    dp.startup.register(on_startup)
    dp.errors.register(on_error)

    dp.include_router(start_router)
    dp.include_router(report_router)
    dp.include_router(settings_router)
    dp.include_router(employees_router)
    dp.include_router(admin_reports_router)
    dp.include_router(attendance_router)
    dp.include_router(password_router)
    dp.include_router(roles_router)

    jobs = start_scheduled_jobs(bot)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for job in jobs:
            job.cancel()
        await bot.session.close()
        await close_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Bot to'xtatildi.")
