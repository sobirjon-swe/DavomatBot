import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.session import init_db
from database.session import AsyncSessionLocal
from database.crud import seed_districts, get_active_password, create_initial_password

from handlers.start import router as start_router
from handlers.employee.report import router as report_router
from handlers.employee.settings import router as settings_router
from handlers.admin.employees import router as employees_router
from handlers.admin.reports import router as admin_reports_router
from handlers.admin.attendance import router as attendance_router
from handlers.admin.password import router as password_router
from handlers.admin.roles import router as roles_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_districts(session)
        active_pw = await get_active_password(session)
        if not active_pw:
            await create_initial_password(session, "12345")
            logger.info("Default password created: 12345 — change it immediately!")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.startup.register(on_startup)

    dp.include_router(start_router)
    dp.include_router(report_router)
    dp.include_router(settings_router)
    dp.include_router(employees_router)
    dp.include_router(admin_reports_router)
    dp.include_router(attendance_router)
    dp.include_router(password_router)
    dp.include_router(roles_router)

    from aiogram.types import Message, Update

    @dp.channel_post()
    async def detect_channel(message: Message):
        logger.info(f"KANAL ANIQLANDI: id={message.chat.id} nomi={message.chat.title}")

    @dp.update()
    async def log_all_updates(update: Update):
        logger.info(f"ANY UPDATE: {update.model_dump_json()[:300]}")

    logger.info("Bot ishga tushdi...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types() + ["channel_post"])
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
