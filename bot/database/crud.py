from datetime import datetime, date
from typing import Optional
import bcrypt
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    User, District, UserDistrict, Report, ReportPartner,
    ReportPhoto, AccessPassword, UserRole, ReportType
)


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
    telegram_id: int,
    full_name: str,
    position: str,
    language: str,
    role: UserRole = UserRole.employee,
) -> User:
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


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    await session.delete(user)
    await session.commit()
    return True


# ─── Districts ──────────────────────────────────────────────────────────────

async def get_all_districts(session: AsyncSession) -> list[District]:
    result = await session.execute(select(District).order_by(District.name_uz))
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
    today = date.today()
    start = datetime(today.year, today.month, today.day)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)
    result = await session.execute(
        select(Report)
        .where(Report.created_at.between(start, end))
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
    start = datetime(search_date.year, search_date.month, search_date.day)
    end = datetime(search_date.year, search_date.month, search_date.day, 23, 59, 59)
    partner_subq = select(ReportPartner.report_id).where(
        ReportPartner.partner_id == user_id
    )
    result = await session.execute(
        select(Report)
        .where(
            Report.created_at.between(start, end),
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
        .where(Report.is_confirmed == False)
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
    if not report:
        return None
    report.is_confirmed = True
    report.confirmed_by = confirmed_by
    report.confirmed_at = datetime.utcnow()
    await session.commit()
    return report


async def reject_report(session: AsyncSession, report_id: int) -> bool:
    report = await get_report_by_id(session, report_id)
    if not report:
        return False
    await session.delete(report)
    await session.commit()
    return True


# ─── Access Password ─────────────────────────────────────────────────────────

async def get_active_password(session: AsyncSession) -> Optional[AccessPassword]:
    result = await session.execute(
        select(AccessPassword).where(AccessPassword.is_active == True).order_by(
            AccessPassword.created_at.desc()
        )
    )
    return result.scalars().first()


async def verify_access_password(session: AsyncSession, raw_password: str) -> bool:
    active_pw = await get_active_password(session)
    if not active_pw:
        return False
    return bcrypt.checkpw(raw_password.encode(), active_pw.password_hash.encode())


async def change_access_password(
    session: AsyncSession, new_password: str, created_by: int
) -> AccessPassword:
    await session.execute(
        AccessPassword.__table__.update().values(is_active=False)
    )
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
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
    hashed = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()
    pw = AccessPassword(password_hash=hashed, is_active=True, created_by=None)
    session.add(pw)
    await session.commit()
    await session.refresh(pw)
    return pw


async def seed_districts(session: AsyncSession) -> None:
    from config import DISTRICTS
    existing = await get_all_districts(session)
    if existing:
        return
    for _, name_uz, name_ru in DISTRICTS:
        district = District(name_uz=name_uz, name_ru=name_ru)
        session.add(district)
    await session.commit()
