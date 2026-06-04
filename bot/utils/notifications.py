from aiogram import Bot
from aiogram.types import InputMediaPhoto
from database.models import Report
from locales import t
from utils.formatters import (
    format_report_type, format_partners, format_datetime, format_district_name
)


async def notify_partners(bot: Bot, report: Report, sender_lang: str = "uz") -> None:
    if not report.partners:
        return

    district_name = format_district_name(report.district, "uz")
    report_type = format_report_type("uz", report.report_type)
    partners_str = format_partners("uz", report.partners)
    date_str = format_datetime(report.created_at)
    photo_ids = [p.file_id for p in report.photos]

    for rp in report.partners:
        partner = rp.partner
        lang = partner.language

        district_name_loc = format_district_name(report.district, lang)
        report_type_loc = format_report_type(lang, report.report_type)
        partners_str_loc = format_partners(lang, report.partners)

        text = t(
            lang, "partner_notified",
            sender=report.user.full_name,
            position=report.user.position,
            report_type=report_type_loc,
            district=district_name_loc,
            customer=report.customer_name,
            partners=partners_str_loc,
            date=date_str,
        )

        try:
            if not photo_ids:
                await bot.send_message(
                    chat_id=partner.telegram_id,
                    text=text,
                    parse_mode="HTML",
                )
            elif len(photo_ids) == 1:
                await bot.send_photo(
                    chat_id=partner.telegram_id,
                    photo=photo_ids[0],
                    caption=text,
                    parse_mode="HTML",
                )
            else:
                from aiogram.types import InputMediaPhoto
                media = [
                    InputMediaPhoto(
                        media=fid,
                        caption=text if i == 0 else None,
                        parse_mode="HTML" if i == 0 else None,
                    )
                    for i, fid in enumerate(photo_ids)
                ]
                await bot.send_media_group(chat_id=partner.telegram_id, media=media)
        except Exception:
            pass


async def notify_superadmin(bot: Bot, superadmin_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=superadmin_id, text=text, parse_mode="HTML")
    except Exception:
        pass
