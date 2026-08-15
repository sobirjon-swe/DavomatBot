import asyncio
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import bcrypt
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from config import TIMEZONE
from database.models import (
    AccessAttempt,
    AccessPassword,
    District,
    Report,
    ReportPartner,
    ReportPhoto,
    ReportType,
    User,
    UserDistrict,
    UserRole,
    utcnow,
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


def _page(stmt: Select, offset: int, limit: int | None) -> Select:
    """So'rovga LIMIT/OFFSET qo'shadi.

    Sahifalash bazada bajariladi — ro'yxatni to'liq o'qib, keyin Pythonda
    kesish hodimlar soni o'sganda ham xotirani, ham vaqtni behuda sarflaydi.
    """
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return stmt


async def _count(session: AsyncSession, stmt: Select) -> int:
    subquery = stmt.order_by(None).subquery()
    result = await session.execute(select(func.count()).select_from(subquery))
    return int(result.scalar_one())


# ─── Users ─────────────────────────────────────────────────────────────────

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(
            selectinload(User.user_districts).selectinload(UserDistrict.district)
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
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
    telegram_id: int | None = None,
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
) -> User | None:
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
) -> User | None:
    """Oldindan yaratilgan hodim yozuvini Telegram hisobiga bog'laydi.

    Yozuv allaqachon band bo'lsa None qaytaradi — bu ikki kishi bitta
    hodimni tanlab qo'yishining oldini oladi. `telegram_id IS NULL` shartini
    UPDATE ichida tekshirish (o'qib-keyin-yozish emas) ikki kishi bir vaqtda
    bitta yozuvni band qilishga urinishini bir xil natijaga olib keladi.
    """
    result = await session.execute(
        update(User)
        .where(User.id == user_id, User.telegram_id.is_(None))
        .values(telegram_id=telegram_id, language=language)
    )
    await session.commit()
    if result.rowcount == 0:
        return None
    return await get_user_by_id(session, user_id)


async def get_all_active_employees(session: AsyncSession) -> list[User]:
    return await get_all_users(session, only_active=True)


def _users_stmt(only_active: bool) -> Select:
    stmt = select(User)
    if only_active:
        stmt = stmt.where(User.is_active.is_(True))
    return stmt.order_by(User.full_name)


async def get_all_users(
    session: AsyncSession,
    *,
    only_active: bool = False,
    offset: int = 0,
    limit: int | None = None,
) -> list[User]:
    stmt = _page(_users_stmt(only_active), offset, limit).options(
        selectinload(User.user_districts).selectinload(UserDistrict.district)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_users(session: AsyncSession, *, only_active: bool = False) -> int:
    return await _count(session, _users_stmt(only_active))


async def set_user_active(
    session: AsyncSession, user_id: int, is_active: bool
) -> User | None:
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


async def get_district_by_id(session: AsyncSession, district_id: int) -> District | None:
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
    plots_count: int | None = None,
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


async def get_report_by_id(session: AsyncSession, report_id: int) -> Report | None:
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


_REPORT_RELATIONS = (
    selectinload(Report.user),
    selectinload(Report.district),
    selectinload(Report.partners).selectinload(ReportPartner.partner),
    selectinload(Report.photos),
)


def _reports_stmt(
    *,
    day: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: int | None = None,
    status: str | None = None,
    newest_first: bool = True,
) -> Select:
    """Hisobotlar uchun umumiy so'rov.

    `day` — bitta kun; `date_from`/`date_to` — oraliq (ikkala chekka ham
    kiradi). Oraliq mahalliy kun chegaralari bo'yicha hisoblanadi.

    `user_id` berilganda hodim ham muallif, ham sherik bo'lgan hisobotlar
    qamrab olinadi. `status` — "pending", "confirmed" yoki "rejected".
    """
    stmt = select(Report)

    if day is not None:
        date_from = date_to = day

    if date_from is not None:
        stmt = stmt.where(Report.created_at >= _day_bounds(date_from)[0])
    if date_to is not None:
        # Oxirgi kun ham to'liq kiradi: keyingi kun boshigacha
        stmt = stmt.where(Report.created_at < _day_bounds(date_to)[1])

    if user_id is not None:
        partner_subq = select(ReportPartner.report_id).where(
            ReportPartner.partner_id == user_id
        )
        stmt = stmt.where(
            or_(Report.user_id == user_id, Report.id.in_(partner_subq))
        )

    if status == "pending":
        stmt = stmt.where(
            Report.is_confirmed.is_(False), Report.is_rejected.is_(False)
        )
    elif status == "confirmed":
        stmt = stmt.where(Report.is_confirmed.is_(True))
    elif status == "rejected":
        stmt = stmt.where(Report.is_rejected.is_(True))

    order = Report.created_at.desc() if newest_first else Report.created_at.asc()
    return stmt.order_by(order)


async def list_reports(
    session: AsyncSession,
    *,
    day: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: int | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> list[Report]:
    """Filtrlangan hisobotlar ro'yxati — API va eksport uchun umumiy kirish."""
    return await _fetch_reports(
        session,
        _reports_stmt(
            day=day,
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            status=status,
        ),
        offset,
        limit,
    )


async def count_reports(
    session: AsyncSession,
    *,
    day: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: int | None = None,
    status: str | None = None,
) -> int:
    return await _count(
        session,
        _reports_stmt(
            day=day,
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            status=status,
        ),
    )


async def _fetch_reports(
    session: AsyncSession, stmt: Select, offset: int, limit: int | None
) -> list[Report]:
    result = await session.execute(_page(stmt, offset, limit).options(*_REPORT_RELATIONS))
    return list(result.scalars().all())


async def get_today_reports(
    session: AsyncSession, *, offset: int = 0, limit: int | None = None
) -> list[Report]:
    return await _fetch_reports(
        session, _reports_stmt(day=local_today()), offset, limit
    )


async def count_today_reports(session: AsyncSession) -> int:
    return await _count(session, _reports_stmt(day=local_today()))


async def get_reports_by_date_and_user(
    session: AsyncSession,
    search_date: date,
    user_id: int,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[Report]:
    return await _fetch_reports(
        session, _reports_stmt(day=search_date, user_id=user_id), offset, limit
    )


async def count_reports_by_date_and_user(
    session: AsyncSession, search_date: date, user_id: int
) -> int:
    return await _count(session, _reports_stmt(day=search_date, user_id=user_id))


async def get_unconfirmed_reports(
    session: AsyncSession, *, offset: int = 0, limit: int | None = None
) -> list[Report]:
    return await _fetch_reports(
        session,
        _reports_stmt(status="pending", newest_first=False),
        offset,
        limit,
    )


async def get_employees_without_report(
    session: AsyncSession, day: date, *, only_role: UserRole | None = None
) -> list[User]:
    """Berilgan kunda hisobotda umuman qatnashmagan faol hodimlar.

    Sherik sifatida qo'shilgan hodim ham ishda bo'lgan hisoblanadi,
    shuning uchun u ro'yxatga tushmaydi.

    `only_role` berilsa faqat o'sha roldagilar qaytariladi — kunlik
    eslatma odatda faqat hodimlarga yuboriladi, rahbarlarga emas.
    """
    start, end = _day_bounds(day)

    authors = select(Report.user_id).where(
        Report.created_at >= start, Report.created_at < end
    )
    partners = (
        select(ReportPartner.partner_id)
        .join(Report, Report.id == ReportPartner.report_id)
        .where(Report.created_at >= start, Report.created_at < end)
    )

    stmt = (
        select(User)
        .where(
            User.is_active.is_(True),
            User.id.not_in(authors.union(partners)),
        )
        .order_by(User.full_name)
    )
    if only_role is not None:
        stmt = stmt.where(User.role == only_role)

    result = await session.execute(
        stmt.options(selectinload(User.user_districts).selectinload(UserDistrict.district))
    )
    return list(result.scalars().all())


async def get_admins(session: AsyncSession) -> list[User]:
    """Xabar yuborish mumkin bo'lgan adminlar (botga kirgan va faol)."""
    result = await session.execute(
        select(User)
        .where(
            User.is_active.is_(True),
            User.telegram_id.is_not(None),
            User.role.in_([UserRole.admin, UserRole.superadmin]),
        )
        .order_by(User.full_name)
    )
    return list(result.scalars().all())


async def count_unconfirmed_reports(session: AsyncSession) -> int:
    return await _count(session, _reports_stmt(status="pending"))


async def confirm_report(
    session: AsyncSession, report_id: int, confirmed_by: int
) -> Report | None:
    """Hisobotni tasdiqlaydi.

    `is_confirmed`/`is_rejected` shartini UPDATE ichida tekshirish ikki admin
    bir vaqtda bitta hisobotni tasdiqlash/rad etishga uringanda faqat
    bittasi o'tishini kafolatlaydi (o'qib-keyin-yozishda ikkalasi ham
    o'tib ketishi mumkin edi).
    """
    result = await session.execute(
        update(Report)
        .where(
            Report.id == report_id,
            Report.is_confirmed.is_(False),
            Report.is_rejected.is_(False),
        )
        .values(is_confirmed=True, confirmed_by=confirmed_by, confirmed_at=utcnow())
    )
    await session.commit()
    if result.rowcount == 0:
        return None
    return await get_report_by_id(session, report_id)


async def revert_report_confirmation(session: AsyncSession, report_id: int) -> None:
    """`confirm_report` dan keyin kanalga yuborish muvaffaqiyatsiz bo'lsa chaqiriladi.

    Hisobot qayta tasdiqlash uchun ochiq holatga qaytariladi.
    """
    await session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(is_confirmed=False, confirmed_by=None, confirmed_at=None)
    )
    await session.commit()


async def reject_report(
    session: AsyncSession, report_id: int, rejected_by: int
) -> Report | None:
    """Hisobotni rad etadi.

    Yozuv o'chirilmaydi — kim, qachon rad etgani saqlanib qoladi. Shart
    UPDATE ichida tekshiriladi — sabab confirm_report bilan bir xil.
    """
    result = await session.execute(
        update(Report)
        .where(
            Report.id == report_id,
            Report.is_confirmed.is_(False),
            Report.is_rejected.is_(False),
        )
        .values(is_rejected=True, rejected_by=rejected_by, rejected_at=utcnow())
    )
    await session.commit()
    if result.rowcount == 0:
        return None
    return await get_report_by_id(session, report_id)


# ─── Access Password ─────────────────────────────────────────────────────────

async def get_active_password(session: AsyncSession) -> AccessPassword | None:
    result = await session.execute(
        select(AccessPassword)
        .where(AccessPassword.is_active.is_(True))
        .order_by(AccessPassword.created_at.desc())
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
) -> AccessAttempt | None:
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
