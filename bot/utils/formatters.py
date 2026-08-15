import html
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from database.models import Report, ReportType
from locales import t

TASHKENT_TZ = ZoneInfo(config.TIMEZONE)
UTC = ZoneInfo("UTC")


def esc(value) -> str:
    """Foydalanuvchi kiritgan matnni HTML uchun xavfsiz qiladi.

    Xabarlar parse_mode="HTML" bilan yuboriladi, shuning uchun ism yoki
    buyurtmachi nomidagi `<`, `>`, `&` belgilari Telegram tomonidan teg deb
    o'qilib, xabar umuman yuborilmay qolardi.
    """
    return html.escape(str(value), quote=False)


def format_report_type(lang: str, report_type: str) -> str:
    mapping = {
        ReportType.laboratory: t(lang, "type_laboratory"),
        ReportType.visual: t(lang, "type_visual"),
        ReportType.instrumental: t(lang, "type_instrumental"),
    }
    return mapping.get(report_type, str(report_type))


def format_partners(lang: str, partners) -> str:
    if not partners:
        return "—"
    return ", ".join(esc(rp.partner.full_name) for rp in partners)


def format_datetime(dt: datetime, lang: str = "uz") -> str:
    # Eski yozuvlar naive bo'lishi mumkin — ular UTC deb qabul qilinadi.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(TASHKENT_TZ).strftime("%d.%m.%Y | %H:%M")


def format_location_url(lat: float, lon: float) -> str:
    google = f"https://maps.google.com/?q={lat},{lon}"
    yandex = f"https://yandex.com/maps/?ll={lon},{lat}&amp;z=17"
    return f'<a href="{google}">Google Maps</a> | <a href="{yandex}">Yandex Maps</a>'


def format_role(lang: str, role: str) -> str:
    roles = {
        "superadmin": "Super Admin",
        "admin": "Admin",
        "employee": "Hodim" if lang == "uz" else "Сотрудник",
    }
    return roles.get(role, role)


def format_district_name(district, lang: str) -> str:
    return esc(district.name_uz if lang == "uz" else district.name_ru)


def format_user_districts(user_districts, lang: str) -> str:
    if not user_districts:
        return "—"
    return ", ".join(
        esc(ud.district.name_uz if lang == "uz" else ud.district.name_ru)
        for ud in user_districts
    )


def build_report_caption(lang: str, report: Report, for_channel: bool = False) -> str:
    key = "channel_report" if for_channel else "report_card"
    return t(
        lang, key,
        full_name=esc(report.user.full_name),
        position=esc(report.user.position),
        report_type=format_report_type(lang, report.report_type),
        district=format_district_name(report.district, lang),
        customer=esc(report.customer_name),
        partners=format_partners(lang, report.partners),
        date=format_datetime(report.created_at),
        location=format_location_url(report.location_lat, report.location_lon),
    )
