import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import config

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo(config.TIMEZONE)


def next_run_at(at: time, *, weekdays: frozenset[int], now: datetime) -> datetime:
    """`now` dan keyingi eng yaqin mos vaqtni topadi.

    Ataylab qat'iy "keyin": agar bugungi vaqt allaqachon o'tgan bo'lsa,
    ertangi kun olinadi. Shu tufayli bot vazifa bajarilgandan keyin qayta
    ishga tushsa ham xabar ikkinchi marta yuborilmaydi.
    """
    candidate = datetime.combine(now.date(), at, tzinfo=LOCAL_TZ)
    if candidate <= now:
        candidate += timedelta(days=1)

    # Dam olish kunlari o'tkazib yuboriladi
    for _ in range(7):
        if candidate.isoweekday() in weekdays:
            return candidate
        candidate += timedelta(days=1)

    # Bu yerga yetib kelish uchun weekdays bo'sh bo'lishi kerak, lekin
    # config uni bo'sh qoldirmaydi.
    raise ValueError("weekdays bo'sh")


async def run_daily(
    name: str,
    at: time,
    job: Callable[[date], Awaitable[None]],
    *,
    weekdays: frozenset[int] | None = None,
) -> None:
    """Har kuni belgilangan mahalliy vaqtda `job` ni chaqiradi.

    Vazifa ichidagi xato butun siklni to'xtatmaydi — logga yozilib,
    keyingi kun qaytadan urinib ko'riladi.

    Agar bot o'sha vaqtda o'chiq bo'lsa, o'tkazib yuborilgan kun
    qaytarilmaydi: yarim kechada kelgan eslatma foydadan ko'ra chalg'itadi.
    """
    days = weekdays if weekdays is not None else config.REMINDER_WEEKDAYS

    while True:
        now = datetime.now(LOCAL_TZ)
        target = next_run_at(at, weekdays=days, now=now)
        delay = (target - now).total_seconds()

        logger.info("%s: keyingi ishga tushish %s", name, target.isoformat())
        await asyncio.sleep(delay)

        try:
            await job(datetime.now(LOCAL_TZ).date())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("%s: vazifa bajarilmadi", name)
