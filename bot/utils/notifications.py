import logging

from aiogram import Bot
from aiogram.types import InputMediaPhoto

from database.models import Report
from locales import t
from utils.formatters import (
    esc, format_datetime, format_district_name, format_partners, format_report_type
)

logger = logging.getLogger(__name__)


async def _send(bot: Bot, chat_id: int, text: str, photo_ids: list[str]) -> None:
    if not photo_ids:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    elif len(photo_ids) == 1:
        await bot.send_photo(
            chat_id=chat_id, photo=photo_ids[0], caption=text, parse_mode="HTML"
        )
    else:
        media = [
            InputMediaPhoto(
                media=fid,
                caption=text if i == 0 else None,
                parse_mode="HTML" if i == 0 else None,
            )
            for i, fid in enumerate(photo_ids)
        ]
        await bot.send_media_group(chat_id=chat_id, media=media)


async def notify_partners(bot: Bot, report: Report, sender_lang: str = "uz") -> None:
    if not report.partners:
        return

    date_str = format_datetime(report.created_at)
    photo_ids = [p.file_id for p in report.photos]

    for rp in report.partners:
        partner = rp.partner
        # Admin qo'lda qo'shgan, hali botga kirmagan hodimga xabar yuborib
        # bo'lmaydi — uni jimgina o'tkazib yuboramiz.
        if partner.telegram_id is None:
            continue

        lang = partner.language
        text = t(
            lang, "partner_notified",
            sender=esc(report.user.full_name),
            position=esc(report.user.position),
            report_type=format_report_type(lang, report.report_type),
            district=format_district_name(report.district, lang),
            customer=esc(report.customer_name),
            partners=format_partners(lang, report.partners),
            date=date_str,
        )

        try:
            await _send(bot, partner.telegram_id, text, photo_ids)
        except Exception:
            # Bitta sherikka yetib bormasa ham qolganlariga yuborilishi kerak.
            logger.warning(
                "Sherikka xabar yuborilmadi: user_id=%s telegram_id=%s",
                partner.id, partner.telegram_id, exc_info=True,
            )


async def notify_user(bot: Bot, telegram_id: int, text: str) -> bool:
    """Bitta foydalanuvchiga xabar yuboradi. Xatoni logga yozadi."""
    try:
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
        return True
    except Exception:
        logger.warning(
            "Foydalanuvchiga xabar yuborilmadi: %s", telegram_id, exc_info=True
        )
        return False


async def notify_superadmin(bot: Bot, superadmin_id: int, text: str) -> bool:
    return await notify_user(bot, superadmin_id, text)
