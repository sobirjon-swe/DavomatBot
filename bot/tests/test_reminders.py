from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from database import crud
from database.models import ReportType, UserRole
from utils.reminders import format_missing, send_reminders, send_summary
from utils.scheduler import next_run_at

TZ = ZoneInfo("Asia/Tashkent")
WORKDAYS = frozenset({1, 2, 3, 4, 5})


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=TZ)


# ─── Rejalashtiruvchi ───────────────────────────────────────────────────────

def test_bugungi_vaqt_hali_kelmagan_bolsa_bugun():
    # 2026-06-05 — juma
    result = next_run_at(time(17, 0), weekdays=WORKDAYS, now=at(2026, 6, 5, 9))

    assert result == at(2026, 6, 5, 17)


def test_vaqt_otgan_bolsa_keyingi_ish_kuniga_otadi():
    """Regressiya himoyasi: bot vazifa bajarilgandan keyin qayta ishga
    tushsa, xabar ikkinchi marta yuborilmasligi kerak."""
    # Juma 17:01 -> dushanba (shanba/yakshanba o'tkazib yuboriladi)
    result = next_run_at(time(17, 0), weekdays=WORKDAYS, now=at(2026, 6, 5, 17, 1))

    assert result == at(2026, 6, 8, 17)
    assert result.isoweekday() == 1


def test_aynan_vaqtida_bolsa_keyingi_kunga():
    """`<=` shart: xuddi o'sha soniyada qayta ishga tushsa takror bo'lmaydi."""
    result = next_run_at(time(17, 0), weekdays=WORKDAYS, now=at(2026, 6, 5, 17, 0))

    assert result.date() != date(2026, 6, 5)


def test_dam_olish_kuni_otkazib_yuboriladi():
    # Shanba
    result = next_run_at(time(17, 0), weekdays=WORKDAYS, now=at(2026, 6, 6, 9))

    assert result == at(2026, 6, 8, 17)


def test_hamma_kun_yoqilgan_bolsa_ertaga():
    result = next_run_at(
        time(17, 0), weekdays=frozenset(range(1, 8)), now=at(2026, 6, 6, 18)
    )

    assert result == at(2026, 6, 7, 17)


# ─── Kim hisobot bermadi ────────────────────────────────────────────────────

async def _report(session, author, district_id, partners=()):
    report = await crud.create_report(
        session,
        user_id=author.id,
        report_type=ReportType.visual,
        district_id=district_id,
        customer_name="Buyurtmachi",
        location_lat=41.31,
        location_lon=69.24,
    )
    if partners:
        await crud.add_report_partners(session, report.id, [p.id for p in partners])
    await session.commit()
    return report


async def test_hisobot_bermagan_hodim_royxatga_tushadi(session, employee, districts):
    missing = await crud.get_employees_without_report(session, crud.local_today())

    assert [u.id for u in missing] == [employee.id]


async def test_hisobot_bergan_hodim_royxatda_yoq(session, employee, districts):
    await _report(session, employee, districts[0].id)

    missing = await crud.get_employees_without_report(session, crud.local_today())

    assert missing == []


async def test_sherik_ham_ishda_hisoblanadi(session, employee, admin, districts):
    """Sherik sifatida qo'shilgan hodim ishda bo'lgan — unga eslatma
    yuborilmasligi kerak."""
    await _report(session, admin, districts[0].id, partners=[employee])

    missing = await crud.get_employees_without_report(session, crud.local_today())

    assert employee.id not in [u.id for u in missing]


async def test_faolsiz_hodim_royxatda_yoq(session, employee):
    await crud.set_user_active(session, employee.id, False)

    missing = await crud.get_employees_without_report(session, crud.local_today())

    assert missing == []


async def test_rol_boyicha_filtrlash(session, employee, admin):
    hammasi = await crud.get_employees_without_report(session, crud.local_today())
    faqat_hodimlar = await crud.get_employees_without_report(
        session, crud.local_today(), only_role=UserRole.employee
    )

    assert {u.id for u in hammasi} == {employee.id, admin.id}
    assert [u.id for u in faqat_hodimlar] == [employee.id]


async def test_boshqa_kundagi_hisobot_hisobga_olinmaydi(session, employee, districts):
    """Kecha hisobot bergani bugungi eslatmani bekor qilmaydi."""
    report = await _report(session, employee, districts[0].id)
    report.created_at = report.created_at - timedelta(days=1)
    await session.commit()

    missing = await crud.get_employees_without_report(session, crud.local_today())

    assert [u.id for u in missing] == [employee.id]


# ─── Xabar matni ────────────────────────────────────────────────────────────

def test_hech_kim_qolmasa_boshqa_xabar():
    text = format_missing("uz", date(2026, 6, 5), [])

    assert "05.06.2026" in text
    assert "barcha hodimlar" in text


async def test_royxat_ism_va_lavozimni_korsatadi(session, employee):
    text = format_missing("uz", date(2026, 6, 5), [employee])

    assert "Ali Valiyev" in text
    assert "Muhandis" in text
    assert "1 ta" in text


# ─── Yuborish ───────────────────────────────────────────────────────────────

async def test_eslatma_faqat_hodimga_ketadi(session_factory, employee, admin, fake_bot):
    sent = await send_reminders(fake_bot, crud.local_today(), session_factory=session_factory)

    assert sent == 1
    assert fake_bot.messages[0]["chat_id"] == employee.telegram_id


async def test_botga_kirmagan_hodim_otkazib_yuboriladi(session, session_factory, fake_bot):
    await crud.create_user(session, full_name="Yangi", position="Texnik", language="uz")

    sent = await send_reminders(fake_bot, crud.local_today(), session_factory=session_factory)

    assert sent == 0
    assert fake_bot.messages == []


async def test_bitta_hodim_bloklagani_qolganlarga_xalaqit_bermaydi(
    session, session_factory, employee, fake_bot
):
    await crud.create_user(
        session,
        full_name="Ikkinchi",
        position="Texnik",
        language="uz",
        telegram_id=500010,
    )
    fake_bot.fail_on_send = True

    # Ikkalasi ham xato berdi, lekin funksiya yiqilmadi
    assert await send_reminders(
        fake_bot, crud.local_today(), session_factory=session_factory
    ) == 0


async def test_yakun_adminlarga_ketadi(
    session_factory, employee, admin, superadmin, fake_bot
):
    sent = await send_summary(fake_bot, crud.local_today(), session_factory=session_factory)

    assert sent == 2
    chat_ids = {m["chat_id"] for m in fake_bot.messages}
    assert chat_ids == {admin.telegram_id, superadmin.telegram_id}
    assert "Ali Valiyev" in fake_bot.messages[0]["text"]


@pytest.mark.parametrize("lang, marker", [("uz", "hisobot"), ("ru", "отчёт")])
async def test_yakun_admin_tilida(session, session_factory, admin, fake_bot, lang, marker):
    await crud.update_user(session, admin.id, language=lang)

    await send_summary(fake_bot, crud.local_today(), session_factory=session_factory)

    assert marker in fake_bot.messages[0]["text"].lower()
