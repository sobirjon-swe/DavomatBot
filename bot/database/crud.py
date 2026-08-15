import asyncio
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import bcrypt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import TIMEZONE
from database.models import (
    AccessAttempt, AccessPassword, District, Report, ReportPartner,
    ReportPhoto, User, UserDistrict, UserRole, ReportType, utcnow
)

LOCAL_TZ = ZoneInfo(TIMEZONE)


def local_today() -> date:
    """Mahalliy (Toshkent) vaqt bo'yicha bugungi sana."""
    return datetime.now(LOCAL_TZ).date()


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    """Mahalliy kunning boshi va keyingi kun boshi (yarim ochiq oraliq).

    Bazada vaqtlar UTC da saqlanadi, shuning uchun oraliq mahalliy kun
    chegarasidan hisoblanib, taqqoslash uchun tz-aware qoldiriladi.
    `between` o'rniga `>= start, < end` ishlatiladi — aks holda kun
    oxiridagi soniyaning kasr qismi tushib qolardi.
    """
    start = datetime.combine(day, time.min, tzinfo=LOCAL_TZ)
    return start, start + timedelta(days=1)


# ─── Users ─────────────────────────────────────────────────────────────────

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(
            selectinload(User.user_districts).selectinload(UserDistrict.district)
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.user_districts).selectinload(UserDistrict.district)
        )
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    full_name: str,
    position: str,
    language: str,
    telegram_id: Optional[int] = None,
    role: UserRole = UserRole.employee,
) -> User:
    """Yangi hodim yaratadi.

    `telegram_id` admin qo'lda qo'shgan hodim uchun None bo'ladi — u botga
    birinchi marta kirganda `link_telegram_account` orqali bog'lanadi.
    """
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        position=position,
        language=language,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user_id: int,
    **kwargs,
) -> Optional[User]:
    user = await get_user_by_id(session, user_id)
    if not user:
        return None
    for key, value in kwargs.items():
        setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user


async def get_unlinked_users(session: AsyncSession) -> list[User]:
    """Admin qo'shgan, lekin hali botga kirmagan hodimlar."""
    result = await session.execute(
        select(User)
        .where(User.telegram_id.is_(None), User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return list(result.scalars().all())


async def link_telegram_account(
    session: AsyncSession, user_id: int, telegram_id: int, language: str
) -> Optional[User]:
    """Oldindan yaratilgan hodim yozuvini Telegram hisobiga bog'laydi.

    Yozuv allaqachon band bo'lsa None qaytaradi — bu ikki kishi bitta
    hodimni tanlab qo'yishining oldini oladi.
    """
    user = await get_user_by_id(session, user_id)
    if not user or user.telegram_id is not None:
        return None
    user.telegram_id = telegram_id
    user.language = language
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_active_employees(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User)
        .where(User.is_active == True)
        .options(
            selectinload(User.user_districts).selectinload(UserDistrict.district)
        )
        .order_by(User.full_name)
    )
    return list(result.scalars().all())


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.user_districts).selectinload(UserDistrict.district)
        )
        .order_by(User.full_name)
    )
    return list(result.scalars().all())


async def set_user_active(
    session: AsyncSession, user_id: int, is_active: bool
) -> Optional[User]:
    """Hodimni faolsizlantiradi yoki tiklaydi.

    Yozuv o'chirilmaydi: `users` ni o'chirish `reports` ni ham kaskad
    o'chirib yuborar va davomat tarixi yo'qolardi.
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        return None
    user.is_active = is_active
    await session.commit()
    await session.refresh(user)
    return user


# ─── Districts ──────────────────────────────────────────────────────────────

async def get_all_districts(session: AsyncSession) -> list[District]:
    result = await session.execute(select(District).order_by(District.name_uz))
    return list(result.scalars().all())


async def get_districts_by_ids(
    session: AsyncSession, district_ids: list[int]
) -> list[District]:
    if not district_ids:
        return []
    result = await session.execute(
        select(District).where(District.id.in_(district_ids)).order_by(District.name_uz)
    )
    return list(result.scalars().all())


async def get_district_by_id(session: AsyncSession, district_id: int) -> Optional[District]:
    result = await session.execute(
        select(District).where(District.id == district_id)
    )
    return result.scalar_one_or_none()


async def set_user_districts(
    session: AsyncSession, user_id: int, district_ids: list[int]
) -> None:
    await session.execute(
        UserDistrict.__table__.delete().where(UserDistrict.user_id == user_id)
    )
    for district_id in district_ids:
        ud = UserDistrict(user_id=user_id, district_id=district_id)
        session.add(ud)
    await session.commit()


async def get_user_district_ids(session: AsyncSession, user_id: int) -> list[int]:
    result = await session.execute(
        select(UserDistrict.district_id).where(UserDistrict.user_id == user_id)
    )
    return list(result.scalars().all())


# ─── Reports ────────────────────────────────────────────────────────────────

async def create_report(
    session: AsyncSession,
    user_id: int,
    report_type: ReportType,
    district_id: int,
    customer_name: str,
    location_lat: float,
    location_lon: float,
    plots_count: Optional[int] = None,
) -> Report:
    report = Report(
        user_id=user_id,
        report_type=report_type,
        district_id=district_id,
        customer_name=customer_name,
        location_lat=location_lat,
        location_lon=location_lon,
        plots_count=plots_count,
    )
    session.add(report)
    await session.flush()
    return report


async def add_report_partners(
    session: AsyncSession, report_id: int, partner_ids: list[int]
) -> None:
    for partner_id in partner_ids:
        rp = ReportPartner(report_id=report_id, partner_id=partner_id)
        session.add(rp)


async def add_report_photos(
    session: AsyncSession, report_id: int, file_ids: list[str]
) -> None:
    for file_id in file_ids:
        photo = ReportPhoto(report_id=report_id, file_id=file_id)
        session.add(photo)


async def get_report_by_id(session: AsyncSession, report_id: int) -> Optional[Report]:
    result = await session.execute(
        select(Report)
        .where(Report.id == report_id)
        .options(
            selectinload(Report.user),
            selectinload(Report.district),
            selectinload(Report.partners).selectinload(ReportPartner.partner),
            selectinload(Report.photos),
        )
    )
    return result.scalar_one_or_none()


async def get_today_reports(session: AsyncSession) -> list[Report]:
    start, end = _day_bounds(local_today())
    result = await session.execute(
        select(Report)
        .where(Report.created_at >= start, Report.created_at < end)
        .options(
            selectinload(Report.user),
            selectinload(Report.district),
            selectinload(Report.partners).selectinload(ReportPartner.partner),
            selectinload(Report.photos),
        )
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_reports_by_date_and_user(
    session: AsyncSession, search_date: date, user_id: int
) -> list[Report]:
    start, end = _day_bounds(search_date)
    partner_subq = select(ReportPartner.report_id).where(
        ReportPartner.partner_id == user_id
    )
    result = await session.execute(
        select(Report)
        .where(
            Report.created_at >= start,
            Report.created_at < end,
            or_(
                Report.user_id == user_id,
                Report.id.in_(partner_subq),
            ),
        )
        .options(
            selectinload(Report.user),
            selectinload(Report.district),
            selectinload(Report.partners).selectinload(ReportPartner.partner),
            selectinload(Report.photos),
        )
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_unconfirmed_reports(session: AsyncSession) -> list[Report]:
    result = await session.execute(
        select(Report)
        .where(Report.is_confirmed.is_(False), Report.is_rejected.is_(False))
        .options(
            selectinload(Report.user),
            selectinload(Report.district),
            selectinload(Report.partners).selectinload(ReportPartner.partner),
            selectinload(Report.photos),
        )
        .order_by(Report.created_at.asc())
    )
    return list(result.scalars().all())


async def confirm_report(
    session: AsyncSession, report_id: int, confirmed_by: int
) -> Optional[Report]:
    report = await get_report_by_id(session, report_id)
    if not report or report.is_confirmed or report.is_rejected:
        return None
    report.is_confirmed = True
    report.confirmed_by = confirmed_by
    report.confirmed_at = utcnow()
    await session.commit()
    return report


async def reject_report(
    session: AsyncSession, report_id: int, rejected_by: int
) -> Optional[Report]:
    """Hisobotni rad etadi.

    Yozuv o'chirilmaydi — kim, qachon rad etgani saqlanib qoladi.
    """
    report = await get_report_by_id(session, report_id)
    if not report or report.is_confirmed or report.is_rejected:
        return None
    report.is_rejected = True
    report.rejected_by = rejected_by
    report.rejected_at = utcnow()
    await session.commit()
    return report


# ─── Access Password ─────────────────────────────────────────────────────────

async def get_active_password(session: AsyncSession) -> Optional[AccessPassword]:
    result = await session.execute(
        select(AccessPassword).where(AccessPassword.is_active == True).order_by(
            AccessPassword.created_at.desc()
        )
    )
    return result.scalars().first()


async def _hash_password(raw_password: str) -> str:
    # bcrypt ataylab sekin va CPU ni band qiladi. To'g'ridan-to'g'ri chaqirilsa
    # butun bot event loop i ~0.3 soniya qotib qoladi, shuning uchun alohida
    # oqimga chiqariladi.
    return await asyncio.to_thread(
        lambda: bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()
    )


async def verify_access_password(session: AsyncSession, raw_password: str) -> bool:
    active_pw = await get_active_password(session)
    if not active_pw:
        return False
    return await asyncio.to_thread(
        bcrypt.checkpw, raw_password.encode(), active_pw.password_hash.encode()
    )


async def change_access_password(
    session: AsyncSession, new_password: str, created_by: int
) -> AccessPassword:
    await session.execute(
        AccessPassword.__table__.update().values(is_active=False)
    )
    hashed = await _hash_password(new_password)
    new_pw = AccessPassword(
        password_hash=hashed,
        is_active=True,
        created_by=created_by,
    )
    session.add(new_pw)
    await session.commit()
    await session.refresh(new_pw)
    return new_pw


async def create_initial_password(
    session: AsyncSession, raw_password: str
) -> AccessPassword:
    hashed = await _hash_password(raw_password)
    pw = AccessPassword(password_hash=hashed, is_active=True, created_by=None)
    session.add(pw)
    await session.commit()
    await session.refresh(pw)
    return pw


# ─── Parol urinishlari ───────────────────────────────────────────────────────

async def get_access_attempt(
    session: AsyncSession, telegram_id: int
) -> Optional[AccessAttempt]:
    result = await session.execute(
        select(AccessAttempt).where(AccessAttempt.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def is_access_blocked(session: AsyncSession, telegram_id: int) -> bool:
    attempt = await get_access_attempt(session, telegram_id)
    return bool(attempt and attempt.is_blocked)


async def register_failed_attempt(
    session: AsyncSession, telegram_id: int, max_attempts: int
) -> tuple[int, bool]:
    """Xato urinishni yozadi. (urinishlar soni, bloklandimi) qaytaradi."""
    attempt = await get_access_attempt(session, telegram_id)
    if attempt is None:
        attempt = AccessAttempt(telegram_id=telegram_id, failed_count=0)
        session.add(attempt)

    attempt.failed_count += 1
    attempt.updated_at = utcnow()
    if attempt.failed_count >= max_attempts:
        attempt.is_blocked = True

    await session.commit()
    return attempt.failed_count, attempt.is_blocked


async def reset_access_attempts(session: AsyncSession, telegram_id: int) -> None:
    attempt = await get_access_attempt(session, telegram_id)
    if attempt is None:
        return
    attempt.failed_count = 0
    attempt.is_blocked = False
    attempt.updated_at = utcnow()
    await session.commit()


# ─── Tumanlar seed ───────────────────────────────────────────────────────────

async def seed_districts(session: AsyncSession) -> int:
    """config.DISTRICTS dagi tumanlarni bazaga qo'shadi.

    Ilgari bu funksiya bitta ham tuman bo'lsa darhol qaytib ketardi, shu
    sababli ro'yxatga keyin qo'shilgan tumanlar hech qachon bazaga
    tushmasdi. Endi faqat yo'qlari qo'shiladi.
    """
    from config import DISTRICTS

    existing = {d.name_uz for d in await get_all_districts(session)}
    added = 0
    for name_uz, name_ru in DISTRICTS:
        if name_uz in existing:
            continue
        session.add(District(name_uz=name_uz, name_ru=name_ru))
        added += 1

    if added:
        await session.commit()
    return added
