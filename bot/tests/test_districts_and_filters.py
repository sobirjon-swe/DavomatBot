import config
from database import crud
from database.models import User, UserRole
from filters.roles import IsAdmin, IsSuperAdmin

# ─── Tumanlar seed ──────────────────────────────────────────────────────────

async def test_seed_takrorlanmaydi(session):
    birinchi = await crud.seed_districts(session)
    ikkinchi = await crud.seed_districts(session)

    assert birinchi == len(config.DISTRICTS)
    assert ikkinchi == 0


async def test_seed_yangi_tumanni_qoshadi(session, monkeypatch):
    """Regressiya: ilgari bazada bitta tuman bo'lsa ham funksiya darhol
    qaytib ketardi, shuning uchun ro'yxatga keyin qo'shilgan tumanlar
    hech qachon bazaga tushmasdi."""
    await crud.seed_districts(session)
    boshlangich = len(await crud.get_all_districts(session))

    monkeypatch.setattr(
        config, "DISTRICTS", [*config.DISTRICTS, ("Sinov tumani", "Тестовый район")]
    )
    qoshildi = await crud.seed_districts(session)

    hammasi = await crud.get_all_districts(session)
    assert qoshildi == 1
    assert len(hammasi) == boshlangich + 1
    assert "Sinov tumani" in [d.name_uz for d in hammasi]


async def test_toshkent_shahar_royxatda_bor(session):
    await crud.seed_districts(session)

    nomlar = [d.name_uz for d in await crud.get_all_districts(session)]

    assert "Toshkent shahar" in nomlar


async def test_hodim_tumanlarini_belgilash(session, employee, districts):
    tanlangan = [districts[0].id, districts[2].id]

    await crud.set_user_districts(session, employee.id, tanlangan)

    assert sorted(await crud.get_user_district_ids(session, employee.id)) == sorted(tanlangan)


async def test_tumanlarni_qayta_belgilash_eskisini_almashtiradi(session, employee, districts):
    await crud.set_user_districts(session, employee.id, [districts[0].id, districts[1].id])
    await crud.set_user_districts(session, employee.id, [districts[3].id])

    assert await crud.get_user_district_ids(session, employee.id) == [districts[3].id]


# ─── Rol filtrlari ──────────────────────────────────────────────────────────

def _user(role: UserRole, is_active: bool = True) -> User:
    user = User()
    user.role = role
    user.is_active = is_active
    return user


async def test_hodim_admin_amallariga_kira_olmaydi():
    assert await IsAdmin()(None, db_user=_user(UserRole.employee)) is False


async def test_admin_va_superadmin_admin_filtridan_otadi():
    assert await IsAdmin()(None, db_user=_user(UserRole.admin)) is True
    assert await IsAdmin()(None, db_user=_user(UserRole.superadmin)) is True


async def test_faolsizlantirilgan_admin_otmaydi():
    """Faolsizlantirilgan adminning chatida eski inline tugmalar qolishi
    mumkin — ular endi ishlamasligi kerak."""
    assert await IsAdmin()(None, db_user=_user(UserRole.admin, is_active=False)) is False


async def test_royxatdan_otmagan_foydalanuvchi_otmaydi():
    assert await IsAdmin()(None, db_user=None) is False


async def test_admin_superadmin_amallariga_kira_olmaydi():
    assert await IsSuperAdmin()(None, db_user=_user(UserRole.admin)) is False
    assert await IsSuperAdmin()(None, db_user=_user(UserRole.superadmin)) is True
