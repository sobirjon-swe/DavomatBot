import logging

from aiogram import Bot
from aiogram.types import InputMediaPhoto

from config import CHANNEL_ID
from database.models import Report
from utils.formatters import build_report_caption

logger = logging.getLogger(__name__)


async def send_report_to_channel(bot: Bot, report: Report) -> tuple[bool, str | None]:
    """Tasdiqlangan hisobotni kanalga yuboradi.

    (muvaffaqiyat, xato_matni) juftligini qaytaradi. Ilgari funksiya
    `bool` deb e'lon qilinib, xatolik yuz berganda matn qaytarardi.
    """
    caption = build_report_caption("uz", report, for_channel=True)
    photo_ids = [p.file_id for p in report.photos]

    try:
        if not photo_ids:
            await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="HTML")
        elif len(photo_ids) == 1:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo_ids[0],
                caption=caption,
                parse_mode="HTML",
            )
        else:
            media = [
                InputMediaPhoto(
                    media=file_id,
                    caption=caption if i == 0 else None,
                    parse_mode="HTML" if i == 0 else None,
                )
                for i, file_id in enumerate(photo_ids)
            ]
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        return True, None
    except Exception as exc:
        logger.exception(
            "Hisobot #%s ni kanalga yuborib bo'lmadi (CHANNEL_ID=%s)",
            report.id, CHANNEL_ID,
        )
        return False, str(exc)
