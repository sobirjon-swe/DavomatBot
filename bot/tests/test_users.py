from database import crud
from database.models import ReportType, UserRole


async def test_bir_nechta_hodim_telegram_id_siz_yaratiladi(session):
    """Regressiya: ilgari telegram_id=0 yozilar va ikkinchi hodimda
    unique cheklov buzilib, admin panel qulab tushardi."""
    first = await crud.create_user(session, full_name="Ali", position="Muhandis", language="uz")
    second = await crud.create_user(session, full_name="Vali", position="Texnik", language="uz")

    assert first.telegram_id is None
    assert second.telegram_id is None
    assert first.id != second.id


async def test_boglanmagan_hodimlar_royxati(session, employee):
    await crud.create_user(session, full_name="Vali", position="Texnik", language="uz")

    unlinked = await crud.get_unlinked_users(session)

    # Telegram hisobiga ega hodim ro'yxatga tushmaydi
    assert [u.full_name for u in unlinked] == ["Vali"]


async def test_hisobni_boglash_bir_martalik(session):
    user = await crud.create_user(session, full_name="Vali", position="Texnik", language="uz")

    linked = await crud.link_telegram_account(session, user.id, 777001, "ru")
    assert linked is not None
    assert linked.telegram_id == 777001
    assert linked.language == "ru"

    # Ikkinchi kishi o'sha yozuvni o'zlashtira olmaydi
    assert await crud.link_telegram_account(session, user.id, 777002, "uz") is None


async def test_faolsizlantirish_hisobotlarni_saqlaydi(session, employee, districts):
    report = await crud.create_report(
        session,
        user_id=employee.id,
        report_type=ReportType.visual,
        district_id=districts[0].id,
        customer_name="Buyurtmachi",
        location_lat=41.3,
        location_lon=69.2,
    )
    await session.commit()

    await crud.set_user_active(session, employee.id, False)

    # Yozuv ham, hisobot ham joyida — o'chirish kaskad qilib yo'q qilardi
    assert await crud.get_user_by_id(session, employee.id) is not None
    assert await crud.get_report_by_id(session, report.id) is not None


async def test_faolsiz_hodim_sherik_royxatida_chiqmaydi(session, employee, admin):
    await crud.set_user_active(session, employee.id, False)

    active = await crud.get_all_active_employees(session)

    assert employee.id not in [u.id for u in active]
    assert admin.id in [u.id for u in active]


async def test_rolni_ozgartirish(session, employee):
    updated = await crud.update_user(session, employee.id, role=UserRole.admin)

    assert updated.role == UserRole.admin


async def test_foydalanuvchilarni_sahifalash(session):
    for i in range(7):
        await crud.create_user(
            session, full_name=f"Hodim {i:02d}", position="Muhandis", language="uz"
        )

    assert await crud.count_users(session) == 7

    first_page = await crud.get_all_users(session, offset=0, limit=3)
    second_page = await crud.get_all_users(session, offset=3, limit=3)
    last_page = await crud.get_all_users(session, offset=6, limit=3)

    assert [u.full_name for u in first_page] == ["Hodim 00", "Hodim 01", "Hodim 02"]
    assert [u.full_name for u in second_page] == ["Hodim 03", "Hodim 04", "Hodim 05"]
    assert len(last_page) == 1


async def test_faqat_faollarni_sanash(session, employee, admin):
    await crud.set_user_active(session, employee.id, False)

    assert await crud.count_users(session) == 2
    assert await crud.count_users(session, only_active=True) == 1
