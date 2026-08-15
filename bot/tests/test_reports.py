from datetime import date, datetime, timedelta, timezone

import pytest

from database import crud
from database.models import ReportType


async def _make_report(session, user_id, district_id, *, created_at=None, customer="Buyurtmachi"):
    report = await crud.create_report(
        session,
        user_id=user_id,
        report_type=ReportType.laboratory,
        district_id=district_id,
        customer_name=customer,
        location_lat=41.31,
        location_lon=69.24,
        plots_count=3,
    )
    if created_at is not None:
        report.created_at = created_at
    await session.commit()
    return report


# ─── Vaqt mintaqasi ─────────────────────────────────────────────────────────

def test_kun_oraligi_toshkent_boyicha():
    start, end = crud._day_bounds(date(2026, 6, 5))

    assert start.utcoffset() == timedelta(hours=5)
    assert end - start == timedelta(days=1)
    assert start.isoformat().startswith("2026-06-05T00:00:00")


def test_kun_oraligi_yarim_ochiq():
    """23:59:59 dan keyingi soniya ulushlari tushib qolmasligi kerak —
    ilgari `between(start, 23:59:59)` ishlatilardi."""
    start, end = crud._day_bounds(date(2026, 6, 5))
    oxirgi_lahza = end - timedelta(microseconds=1)

    assert start <= oxirgi_lahza < end


@pytest.mark.parametrize(
    "utc_vaqt, kutilgan_kun",
    [
        # Toshkent = UTC+5. UTC 4-iyun 20:00 = Toshkent 5-iyun 01:00
        (datetime(2026, 6, 4, 20, 0, tzinfo=timezone.utc), date(2026, 6, 5)),
        # UTC 5-iyun 18:59 = Toshkent 5-iyun 23:59
        (datetime(2026, 6, 5, 18, 59, tzinfo=timezone.utc), date(2026, 6, 5)),
        # UTC 5-iyun 19:00 = Toshkent 6-iyun 00:00 -> keyingi kun
        (datetime(2026, 6, 5, 19, 0, tzinfo=timezone.utc), date(2026, 6, 6)),
    ],
)
def test_utc_vaqt_togri_toshkent_kuniga_tushadi(utc_vaqt, kutilgan_kun):
    start, end = crud._day_bounds(kutilgan_kun)

    assert start <= utc_vaqt < end


@pytest.mark.requires_pg
async def test_sana_boyicha_qidiruv_toshkent_kunini_oladi(session, employee, districts):
    """Kechqurun UTC bo'yicha keyingi kunga o'tib ketgan hisobot Toshkent
    sanasi bo'yicha topilishi kerak.

    Bu testga TIMESTAMPTZ kerak: SQLite vaqt mintaqasini saqlamaydi va
    taqqoslash noto'g'ri chiqadi. Shuning uchun faqat PostgreSQL da ishlaydi.
    """
    kechqurun = datetime(2026, 6, 4, 20, 30, tzinfo=timezone.utc)  # Toshkent 5-iyun 01:30
    await _make_report(session, employee.id, districts[0].id, created_at=kechqurun)

    besh_iyun = await crud.get_reports_by_date_and_user(session, date(2026, 6, 5), employee.id)
    tort_iyun = await crud.get_reports_by_date_and_user(session, date(2026, 6, 4), employee.id)

    assert len(besh_iyun) == 1
    assert tort_iyun == []


# ─── Tasdiqlash va rad etish ────────────────────────────────────────────────

async def test_rad_etilgan_hisobot_ochirilmaydi(session, employee, admin, districts):
    report = await _make_report(session, employee.id, districts[0].id)

    rejected = await crud.reject_report(session, report.id, admin.id)

    assert rejected.is_rejected is True
    assert rejected.rejected_by == admin.id
    assert rejected.rejected_at is not None
    # Audit izi qolishi kerak — ilgari yozuv butunlay o'chirilardi
    assert await crud.get_report_by_id(session, report.id) is not None


async def test_rad_etilgan_hisobot_kutayotganlar_royxatidan_chiqadi(
    session, employee, admin, districts
):
    report = await _make_report(session, employee.id, districts[0].id)
    assert len(await crud.get_unconfirmed_reports(session)) == 1

    await crud.reject_report(session, report.id, admin.id)

    assert await crud.get_unconfirmed_reports(session) == []
    assert await crud.count_unconfirmed_reports(session) == 0


async def test_hisobot_ikki_marta_ishlanmaydi(session, employee, admin, districts):
    report = await _make_report(session, employee.id, districts[0].id)

    assert await crud.confirm_report(session, report.id, admin.id) is not None
    # Ikki admin bir vaqtda bosishi mumkin — ikkinchisi rad javob olishi kerak
    assert await crud.confirm_report(session, report.id, admin.id) is None
    assert await crud.reject_report(session, report.id, admin.id) is None


async def test_tasdiqlash_maydonlarni_toldiradi(session, employee, admin, districts):
    report = await _make_report(session, employee.id, districts[0].id)

    confirmed = await crud.confirm_report(session, report.id, admin.id)

    assert confirmed.is_confirmed is True
    assert confirmed.confirmed_by == admin.id
    assert confirmed.confirmed_at is not None


# ─── Sheriklar va sahifalash ────────────────────────────────────────────────

async def test_sherik_ham_hisobotni_koradi(session, employee, admin, districts):
    report = await _make_report(session, employee.id, districts[0].id)
    await crud.add_report_partners(session, report.id, [admin.id])
    await session.commit()

    bugun = crud.local_today()
    sherikniki = await crud.get_reports_by_date_and_user(session, bugun, admin.id)

    assert [r.id for r in sherikniki] == [report.id]


async def test_hisobotlarni_sahifalash(session, employee, districts):
    for i in range(5):
        await _make_report(session, employee.id, districts[0].id, customer=f"Mijoz {i}")

    assert await crud.count_today_reports(session) == 5

    birinchi = await crud.get_today_reports(session, offset=0, limit=2)
    oxirgi = await crud.get_today_reports(session, offset=4, limit=2)

    assert len(birinchi) == 2
    assert len(oxirgi) == 1
