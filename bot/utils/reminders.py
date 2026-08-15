import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import date

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_admins, get_employees_without_report
from database.models import User, UserRole
from database.session import AsyncSessionLocal
from keyboards import webapp
from locales import t
from utils.formatters import esc

logger = logging.getLogger(__name__)

# Fon vazifalari o'z sessiyasini ochadi (ular so'rov konteksti ichida
# ishlamaydi). Parametr sifatida berilishi testlarda boshqa bazaga
# ulanish imkonini beradi.
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def format_missing(lang: str, day: date, employees: list[User]) -> str:
    """"Hisobot bermaganlar" ro'yxatini xabar matniga aylantiradi."""
    if not employees:
        return t(lang, "nobody_missing", date=day.strftime("%d.%m.%Y"))

    lines = [
        t(lang, "missing_header", date=day.strftime("%d.%m.%Y"), count=len(employees)),
        "",
    ]
    lines.extend(
        f"• <b>{esc(user.full_name)}</b> — {esc(user.position)}" for user in employees
    )
    return "\n".join(lines)


async def send_reminders(
    bot: Bot, day: date, *, session_factory: SessionFactory = AsyncSessionLocal
) -> int:
    """Bugun hisobot bermagan hodimlarga eslatma yuboradi.

    Faqat `employee` roliga yuboriladi: adminlar hisobotni tasdiqlaydi,
    ularga kunlik eslatma shovqindan boshqa narsa emas.

    Yuborilgan xabarlar sonini qaytaradi.
    """
    async with session_factory() as session:
        employees = await get_employees_without_report(
            session, day, only_role=UserRole.employee
        )

    sent = 0
    for user in employees:
        # Admin qo'shgan, lekin hali botga kirmagan hodimga yozib bo'lmaydi
        if user.telegram_id is None:
            continue

        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=t(user.language, "daily_reminder"),
                parse_mode="HTML",
                reply_markup=webapp.inline_kb(user.language),
            )
            sent += 1
        except Exception:
            # Bitta hodim botni bloklagani qolganlarga xalaqit bermasin
            logger.warning("Eslatma yuborilmadi: user_id=%s", user.id, exc_info=True)

    logger.info("Kunlik eslatma: %s hodimdan %s tasiga yuborildi", len(employees), sent)
    return sent


async def send_summary(
    bot: Bot, day: date, *, session_factory: SessionFactory = AsyncSessionLocal
) -> int:
    """Adminlarga kunlik yakun: kim hisobot bermadi."""
    async with session_factory() as session:
        employees = await get_employees_without_report(
            session, day, only_role=UserRole.employee
        )
        admins = await get_admins(session)

    sent = 0
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.telegram_id,
                text=format_missing(admin.language, day, employees),
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            logger.warning("Yakun yuborilmadi: user_id=%s", admin.id, exc_info=True)

    logger.info(
        "Kunlik yakun: %s ta admin, %s ta hisobot bermagan hodim", sent, len(employees)
    )
    return sent
