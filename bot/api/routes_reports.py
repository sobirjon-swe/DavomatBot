import asyncio
import logging
from datetime import date
from typing import Literal

from aiogram.types import BufferedInputFile
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

import config
from api.deps import AdminUser, BotDep, CurrentUser, SessionDep
from api.schemas import (
    ExportRequest,
    OkOut,
    Page,
    PhotoOut,
    ReportCreate,
    ReportOut,
    UserBrief,
    report_out,
    user_brief,
)
from database.crud import (
    add_report_partners,
    add_report_photos,
    confirm_report,
    count_reports,
    create_report,
    get_all_active_employees,
    get_district_by_id,
    get_employees_without_report,
    get_report_by_id,
    list_reports,
    local_today,
    reject_report,
    revert_report_confirmation,
)
from database.models import Report, ReportType, User, UserRole
from keyboards.pagination import PER_PAGE, page_count
from locales import t
from utils.channel import send_report_to_channel
from utils.export import build_workbook, file_name
from utils.notifications import notify_partners, notify_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


def _is_admin(user: User) -> bool:
    return user.role in (UserRole.admin, UserRole.superadmin)


def _can_see(user: User, report: Report) -> bool:
    if _is_admin(user):
        return True
    return report.user_id == user.id or any(
        rp.partner_id == user.id for rp in report.partners
    )


async def _get_or_404(session, report_id: int) -> Report:
    report = await get_report_by_id(session, report_id)
    if report is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Hisobot topilmadi"},
        )
    return report


def _already_processed() -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT,
        detail={
            "code": "already_processed",
            "message": "Hisobot allaqachon ko'rib chiqilgan",
        },
    )


# ─── O'qish ─────────────────────────────────────────────────────────────────

@router.get("/reports", response_model=Page[ReportOut])
async def list_reports_endpoint(
    user: CurrentUser,
    session: SessionDep,
    day: date | None = None,
    user_id: int | None = None,
    report_status: Literal["pending", "confirmed", "rejected"] | None = Query(
        None, alias="status"
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(PER_PAGE, ge=1, le=100),
) -> Page[ReportOut]:
    # Hodim faqat o'zi qatnashgan hisobotlarni ko'radi — so'rovdagi
    # user_id ga ishonib bo'lmaydi.
    effective_user_id = user_id if _is_admin(user) else user.id

    total = await count_reports(
        session, day=day, user_id=effective_user_id, status=report_status
    )
    reports = await list_reports(
        session,
        day=day,
        user_id=effective_user_id,
        status=report_status,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    return Page(
        items=[report_out(r) for r in reports],
        total=total,
        page=page,
        pages=page_count(total, per_page=per_page),
    )


@router.get("/reports/missing", response_model=list[UserBrief])
async def missing_reports(
    admin: AdminUser,
    session: SessionDep,
    day: date | None = None,
) -> list[UserBrief]:
    """Berilgan kunda hisobotda qatnashmagan hodimlar.

    Yo'l `/reports/{report_id}` dan OLDIN e'lon qilingan — aks holda
    "missing" so'zi report_id sifatida o'qilib, 422 qaytarardi.
    """
    employees = await get_employees_without_report(
        session, day or local_today(), only_role=UserRole.employee
    )
    return [user_brief(e) for e in employees]


@router.post("/reports/export", response_model=OkOut)
async def export_reports(
    payload: ExportRequest, admin: AdminUser, session: SessionDep, bot: BotDep
) -> OkOut:
    """Belgilangan oraliqdagi hisobotlarni Excel qilib botga yuboradi.

    Mini App WebView'da faylni to'g'ridan-to'g'ri yuklab olish ishonchsiz,
    shuning uchun tayyor fayl botning o'zi orqali adminning shaxsiy
    chatiga yuboriladi — xuddi botdagi "Eksport" menyusi kabi.
    """
    if payload.date_from > payload.date_to:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "bad_range", "message": "Sanalar oralig'i noto'g'ri"},
        )
    if (payload.date_to - payload.date_from).days + 1 > config.MAX_EXPORT_DAYS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "range_too_long",
                "message": f"Oraliq {config.MAX_EXPORT_DAYS} kundan oshmasligi kerak",
            },
        )
    if admin.telegram_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "not_linked", "message": "Hisobingiz botga bog'lanmagan"},
        )

    reports = await list_reports(session, date_from=payload.date_from, date_to=payload.date_to)
    if not reports:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "empty", "message": "Bu oraliqda hisobot topilmadi"},
        )

    # openpyxl sinxron ishlaydi; katta oraliqda event loop qotib
    # qolmasligi uchun alohida oqimga chiqariladi (bot chatidagi eksport
    # bilan bir xil yondashuv — utils/export.py).
    workbook = await asyncio.to_thread(build_workbook, admin.language, reports)

    try:
        await bot.send_document(
            chat_id=admin.telegram_id,
            document=BufferedInputFile(
                workbook, filename=file_name(payload.date_from, payload.date_to)
            ),
            caption=t(
                admin.language,
                "export_caption",
                range=(
                    payload.date_from.strftime("%d.%m.%Y")
                    if payload.date_from == payload.date_to
                    else f"{payload.date_from:%d.%m.%Y} - {payload.date_to:%d.%m.%Y}"
                ),
                count=len(reports),
            ),
        )
    except Exception:
        logger.exception("Eksport faylini botga yuborib bo'lmadi (admin id=%s)", admin.id)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": "send_failed", "message": "Faylni botga yuborib bo'lmadi"},
        ) from None

    logger.info(
        "Eksport Mini App orqali botga yuborildi: %s - %s (admin id=%s)",
        payload.date_from, payload.date_to, admin.id,
    )
    return OkOut()


@router.get("/reports/{report_id}", response_model=ReportOut)
async def read_report(
    report_id: int, user: CurrentUser, session: SessionDep
) -> ReportOut:
    report = await _get_or_404(session, report_id)
    if not _can_see(user, report):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Ruxsat yo'q"},
        )
    return report_out(report)


# ─── Yaratish ───────────────────────────────────────────────────────────────

@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report_endpoint(
    payload: ReportCreate, user: CurrentUser, session: SessionDep, bot: BotDep
) -> ReportOut:
    if await get_district_by_id(session, payload.district_id) is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "bad_district", "message": "Tuman topilmadi"},
        )

    partner_ids = [pid for pid in payload.partner_ids if pid != user.id]
    if partner_ids:
        active_ids = {e.id for e in await get_all_active_employees(session)}
        if set(partner_ids) - active_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"code": "bad_partner", "message": "Sherik topilmadi"},
            )

    report = await create_report(
        session,
        user_id=user.id,
        report_type=ReportType(payload.report_type),
        district_id=payload.district_id,
        customer_name=payload.customer_name,
        location_lat=payload.lat,
        location_lon=payload.lon,
        plots_count=payload.plots_count,
    )
    await add_report_partners(session, report.id, partner_ids)
    await add_report_photos(session, report.id, payload.photo_file_ids)
    await session.commit()

    full = await get_report_by_id(session, report.id)
    logger.info("API orqali hisobot #%s yaratildi (hodim id=%s)", report.id, user.id)

    await notify_partners(bot, full, user.language)
    return report_out(full)


# ─── Tasdiqlash ─────────────────────────────────────────────────────────────

@router.post("/reports/{report_id}/approve", response_model=ReportOut)
async def approve(
    report_id: int, admin: AdminUser, session: SessionDep, bot: BotDep
) -> ReportOut:
    report = await _get_or_404(session, report_id)

    # Kanalga yuborishdan oldin hisobotni atom tarzda "band qilamiz" — shunda
    # ikki admin bir vaqtda tasdiqlasa faqat bittasi kanalga xabar yuboradi.
    confirmed = await confirm_report(session, report_id, admin.id)
    if confirmed is None:
        raise _already_processed()

    ok, error = await send_report_to_channel(bot, confirmed)
    if not ok:
        # Kanalga bormagan hisobot tasdiqlangan deb belgilanmaydi.
        await revert_report_confirmation(session, report_id)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "channel_failed",
                "message": "Kanalga yuborib bo'lmadi",
                "error": (error or "")[:200],
            },
        )

    logger.info("Hisobot #%s tasdiqlandi (admin id=%s)", report_id, admin.id)

    if report.user.telegram_id is not None:
        await notify_user(
            bot, report.user.telegram_id,
            t(report.user.language, "report_approved_notify"),
        )

    return report_out(await get_report_by_id(session, report_id))


@router.post("/reports/{report_id}/reject", response_model=ReportOut)
async def reject(
    report_id: int, admin: AdminUser, session: SessionDep, bot: BotDep
) -> ReportOut:
    report = await reject_report(session, report_id, admin.id)
    if report is None:
        raise _already_processed()

    logger.info("Hisobot #%s rad etildi (admin id=%s)", report_id, admin.id)

    if report.user.telegram_id is not None:
        await notify_user(
            bot, report.user.telegram_id,
            t(report.user.language, "report_rejected_notify"),
        )

    return report_out(report)


# ─── Rasm yuklash ───────────────────────────────────────────────────────────

@router.post("/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    user: CurrentUser, bot: BotDep, file: UploadFile = File(...)
) -> PhotoOut:
    """Brauzerdan kelgan rasmni Telegram file_id ga aylantiradi.

    Mini App file_id ishlab chiqara olmaydi, shuning uchun rasm avval yopiq
    ombor chatiga yuboriladi. Shu tufayli bazada va kanalga chiqarishda
    hech nima o'zgarmaydi.
    """
    if not config.STORAGE_CHAT_ID:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "storage_not_configured",
                "message": "STORAGE_CHAT_ID sozlanmagan",
            },
        )

    if file.content_type not in config.ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "bad_type", "message": "Faqat JPEG, PNG yoki WebP"},
        )

    # Cheklovdan bitta bayt ko'p o'qiymiz — shunda haddan oshganini
    # butun faylni xotiraga olmasdan aniqlaymiz.
    payload = await file.read(config.MAX_PHOTO_BYTES + 1)
    if len(payload) > config.MAX_PHOTO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "too_large", "message": "Rasm hajmi juda katta"},
        )
    if not payload:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_file", "message": "Fayl bo'sh"},
        )

    try:
        message = await bot.send_photo(
            chat_id=config.STORAGE_CHAT_ID,
            photo=BufferedInputFile(payload, filename=file.filename or "photo.jpg"),
            caption=f"#upload user_id={user.id}",
        )
    except Exception:
        logger.exception("Rasmni ombor chatiga yuborib bo'lmadi")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upload_failed", "message": "Rasmni saqlab bo'lmadi"},
        ) from None

    return PhotoOut(file_id=message.photo[-1].file_id)


@router.get("/health", response_model=OkOut, tags=["service"])
async def health() -> OkOut:
    return OkOut()
