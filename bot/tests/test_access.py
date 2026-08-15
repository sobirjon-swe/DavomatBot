import config
from database import crud

# ─── Parol ──────────────────────────────────────────────────────────────────

async def test_parol_tekshiruvi(session):
    await crud.create_initial_password(session, "sirli-parol")

    assert await crud.verify_access_password(session, "sirli-parol") is True
    assert await crud.verify_access_password(session, "boshqa-parol") is False


async def test_parol_ochiq_saqlanmaydi(session):
    await crud.create_initial_password(session, "sirli-parol")

    active = await crud.get_active_password(session)

    assert "sirli-parol" not in active.password_hash
    assert active.password_hash.startswith("$2")  # bcrypt


async def test_parol_bolmasa_hech_kim_kira_olmaydi(session):
    assert await crud.verify_access_password(session, "istalgan") is False


async def test_parol_ozgartirilsa_eskisi_ishlamaydi(session, admin):
    await crud.create_initial_password(session, "eski-parol")

    await crud.change_access_password(session, "yangi-parol", admin.id)

    assert await crud.verify_access_password(session, "yangi-parol") is True
    assert await crud.verify_access_password(session, "eski-parol") is False


async def test_faqat_bitta_faol_parol_qoladi(session, admin):
    await crud.create_initial_password(session, "birinchi")
    await crud.change_access_password(session, "ikkinchi", admin.id)
    await crud.change_access_password(session, "uchinchi", admin.id)

    active = await crud.get_active_password(session)
    assert await crud.verify_access_password(session, "uchinchi") is True
    assert active.created_by == admin.id


# ─── Urinishlar va blok ─────────────────────────────────────────────────────

async def test_uch_urinishdan_keyin_bloklanadi(session):
    limit = config.MAX_PASSWORD_ATTEMPTS

    for kutilgan in range(1, limit):
        count, blocked = await crud.register_failed_attempt(session, 999, limit)
        assert (count, blocked) == (kutilgan, False)

    count, blocked = await crud.register_failed_attempt(session, 999, limit)

    assert count == limit
    assert blocked is True
    assert await crud.is_access_blocked(session, 999) is True


async def test_blok_boshqa_foydalanuvchiga_tegmaydi(session):
    limit = config.MAX_PASSWORD_ATTEMPTS
    for _ in range(limit):
        await crud.register_failed_attempt(session, 999, limit)

    assert await crud.is_access_blocked(session, 999) is True
    assert await crud.is_access_blocked(session, 1000) is False


async def test_urinishlarni_tozalash(session):
    limit = config.MAX_PASSWORD_ATTEMPTS
    for _ in range(limit):
        await crud.register_failed_attempt(session, 999, limit)

    await crud.reset_access_attempts(session, 999)

    assert await crud.is_access_blocked(session, 999) is False
    attempt = await crud.get_access_attempt(session, 999)
    assert attempt.failed_count == 0


async def test_blok_bazada_saqlanadi(session):
    """Regressiya: blok xotirada saqlanar va bot restart bo'lishi bilan
    bekor bo'lardi. Endi u yozuv sifatida bazada turadi."""
    limit = config.MAX_PASSWORD_ATTEMPTS
    for _ in range(limit):
        await crud.register_failed_attempt(session, 999, limit)

    saqlangan = await crud.get_access_attempt(session, 999)

    assert saqlangan is not None
    assert saqlangan.is_blocked is True
