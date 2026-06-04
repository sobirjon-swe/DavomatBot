from datetime import datetime
from zoneinfo import ZoneInfo
from database.models import Report, ReportType
from locales import t

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def format_report_type(lang: str, report_type: str) -> str:
    mapping = {
        ReportType.laboratory: t(lang, "type_laboratory"),
        ReportType.visual: t(lang, "type_visual"),
        ReportType.instrumental: t(lang, "type_instrumental"),
    }
    return mapping.get(report_type, report_type)


def format_partners(lang: str, partners) -> str:
    if not partners:
        return "—"
    names = [rp.partner.full_name for rp in partners]
    return ", ".join(names)


def format_datetime(dt: datetime, lang: str = "uz") -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TASHKENT_TZ).strftime("%d.%m.%Y | %H:%M")


def format_location_url(lat: float, lon: float) -> str:
    google = f"https://maps.google.com/?q={lat},{lon}"
    yandex = f"https://yandex.com/maps/?ll={lon},{lat}&z=17"
    return f'<a href="{google}">Google Maps</a> | <a href="{yandex}">Yandex Maps</a>'


def format_role(lang: str, role: str) -> str:
    roles = {
        "superadmin": "Super Admin",
        "admin": "Admin",
        "employee": "Hodim" if lang == "uz" else "Сотрудник",
    }
    return roles.get(role, role)


def format_district_name(district, lang: str) -> str:
    return district.name_uz if lang == "uz" else district.name_ru


def format_user_districts(user_districts, lang: str) -> str:
    if not user_districts:
        return "—"
    names = [
        ud.district.name_uz if lang == "uz" else ud.district.name_ru
        for ud in user_districts
    ]
    return ", ".join(names)


def build_report_caption(lang: str, report: Report, for_channel: bool = False) -> str:
    district_name = format_district_name(report.district, lang)
    report_type = format_report_type(lang, report.report_type)
    partners_str = format_partners(lang, report.partners)
    date_str = format_datetime(report.created_at)
    location_str = format_location_url(report.location_lat, report.location_lon)

    key = "channel_report" if for_channel else "report_card"
    text = t(
        lang, key,
        full_name=report.user.full_name,
        position=report.user.position,
        report_type=report_type,
        district=district_name,
        customer=report.customer_name,
        partners=partners_str,
        date=date_str,
        location=location_str,
    )
    return text
