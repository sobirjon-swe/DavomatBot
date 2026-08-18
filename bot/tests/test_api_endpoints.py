import time

import config
from database import crud
from database.models import ReportType, UserRole
from tests.conftest import auth_header

UNKNOWN_TELEGRAM_ID = 999_999


async def _report(session, author, district_id, customer="Buyurtmachi"):
    report = await crud.create_report(
        session,
        user_id=author.id,
        report_type=ReportType.visual,
        district_id=district_id,
        customer_name=customer,
        location_lat=41.31,
        location_lon=69.24,
    )
    await crud.add_report_photos(session, report.id, ["f1", "f2", "f3"])
    await session.commit()
    return report


# ─── Autentifikatsiya ───────────────────────────────────────────────────────

async def test_sarlavhasiz_sorov_401(api_client):
    response = await api_client.get("/api/me")

    assert response.status_code == 401


async def test_notogri_sxema_401(api_client, employee):
    response = await api_client.get(
        "/api/me", headers={"Authorization": "Bearer nimadir"}
    )

    assert response.status_code == 401


async def test_qalbaki_imzo_401(api_client, employee):
    """Imzo boshqa token bilan qo'yilgan bo'lsa kirish yo'q."""
    response = await api_client.get(
        "/api/me",
        headers=auth_header(employee.telegram_id, bot_token="999:BOSHQA"),
    )

    assert response.status_code == 401


async def test_imzodan_keyin_ozgartirilgan_id_401(api_client, employee, admin):
    """Hodim o'zini admin qilib ko'rsatishga urinadi."""
    response = await api_client.get(
        "/api/me",
        headers=auth_header(employee.telegram_id, tamper_user_id=admin.telegram_id),
    )

    assert response.status_code == 401


async def test_eski_initdata_401(api_client, employee):
    eski = int(time.time()) - 100_000
    response = await api_client.get(
        "/api/me", headers=auth_header(employee.telegram_id, auth_date=eski)
    )

    assert response.status_code == 401


async def test_royxatdan_otmagan_foydalanuvchi_403(api_client):
    response = await api_client.get("/api/me", headers=auth_header(UNKNOWN_TELEGRAM_ID))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "not_registered"


async def test_faolsizlantirilgan_hisob_403(api_client, session, employee):
    await crud.set_user_active(session, employee.id, False)

    response = await api_client.get("/api/me", headers=auth_header(employee.telegram_id))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "deactivated"


# ─── /me ────────────────────────────────────────────────────────────────────

async def test_me_ozini_qaytaradi(api_client, employee, districts, session):
    await crud.set_user_districts(session, employee.id, [districts[0].id])

    response = await api_client.get("/api/me", headers=auth_header(employee.telegram_id))
    body = response.json()

    assert response.status_code == 200
    assert body["id"] == employee.id
    assert body["role"] == "employee"
    assert body["is_linked"] is True
    assert [d["id"] for d in body["districts"]] == [districts[0].id]


async def test_tilni_ozgartirish(api_client, employee):
    response = await api_client.patch(
        "/api/me/language",
        json={"language": "ru"},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 200
    assert response.json()["language"] == "ru"


async def test_notogri_til_rad_etiladi(api_client, employee):
    response = await api_client.patch(
        "/api/me/language",
        json={"language": "de"},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 422


async def test_hamkasblar_royxati_ozini_chiqarmaydi(
    api_client, session, employee, admin
):
    """Sherik tanlashda o'zini tanlash mumkin bo'lmasligi kerak."""
    response = await api_client.get(
        "/api/colleagues", headers=auth_header(employee.telegram_id)
    )
    ids = [u["id"] for u in response.json()]

    assert response.status_code == 200
    assert employee.id not in ids
    assert admin.id in ids


async def test_hamkasblar_faqat_ism_va_lavozim_beradi(api_client, employee, admin):
    response = await api_client.get(
        "/api/colleagues", headers=auth_header(employee.telegram_id)
    )

    assert set(response.json()[0]) == {"id", "full_name", "position"}


async def test_faolsiz_hamkasb_royxatda_yoq(api_client, session, employee, admin):
    await crud.set_user_active(session, admin.id, False)

    response = await api_client.get(
        "/api/colleagues", headers=auth_header(employee.telegram_id)
    )

    assert response.json() == []


async def test_mavjud_bolmagan_tuman_400(api_client, employee, districts):
    response = await api_client.put(
        "/api/me/districts",
        json={"district_ids": [999_999]},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "bad_district"


# ─── Hodimlar ───────────────────────────────────────────────────────────────

async def test_hodim_hodimlar_royxatini_kora_olmaydi(api_client, employee):
    response = await api_client.get(
        "/api/employees", headers=auth_header(employee.telegram_id)
    )

    assert response.status_code == 403


async def test_admin_royxatni_sahifalab_oladi(api_client, session, admin):
    for i in range(7):
        await crud.create_user(
            session, full_name=f"Hodim {i:02d}", position="Muhandis", language="uz"
        )

    response = await api_client.get(
        "/api/employees?page=2&per_page=3", headers=auth_header(admin.telegram_id)
    )
    body = response.json()

    assert response.status_code == 200
    assert body["total"] == 8  # 7 ta + adminning o'zi
    assert body["pages"] == 3
    assert len(body["items"]) == 3


async def test_admin_hodim_qoshadi(api_client, admin, districts):
    response = await api_client.post(
        "/api/employees",
        json={
            "full_name": "Yangi Hodim",
            "position": "Texnik",
            "district_ids": [districts[0].id],
        },
        headers=auth_header(admin.telegram_id),
    )
    body = response.json()

    assert response.status_code == 201
    # Hali botga kirmagan — yozuv bo'sh telegram_id bilan turadi
    assert body["is_linked"] is False
    assert body["full_name"] == "Yangi Hodim"


async def test_admin_hodimni_faolsizlantira_olmaydi(api_client, admin, employee):
    """Faolsizlantirish faqat superadminga."""
    response = await api_client.post(
        f"/api/employees/{employee.id}/deactivate",
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 403


async def test_superadmin_faolsizlantiradi_va_tiklaydi(api_client, superadmin, employee):
    off = await api_client.post(
        f"/api/employees/{employee.id}/deactivate",
        headers=auth_header(superadmin.telegram_id),
    )
    assert off.status_code == 200
    assert off.json()["is_active"] is False

    on = await api_client.post(
        f"/api/employees/{employee.id}/activate",
        headers=auth_header(superadmin.telegram_id),
    )
    assert on.json()["is_active"] is True


async def test_ozini_faolsizlantirib_bolmaydi(api_client, superadmin):
    response = await api_client.post(
        f"/api/employees/{superadmin.id}/deactivate",
        headers=auth_header(superadmin.telegram_id),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "self_deactivate"


async def test_superadmin_rolini_ozgartirib_bolmaydi(api_client, session, superadmin):
    boshqa = await crud.create_user(
        session, full_name="Ikkinchi", position="Rahbar", language="uz",
        telegram_id=500009, role=UserRole.superadmin,
    )

    response = await api_client.patch(
        f"/api/employees/{boshqa.id}/role",
        json={"role": "employee"},
        headers=auth_header(superadmin.telegram_id),
    )

    assert response.status_code == 400


# ─── Kirish paroli ──────────────────────────────────────────────────────────

async def test_admin_parolni_ozgartiradi(api_client, session, admin):
    await crud.create_initial_password(session, "eski-parol")

    response = await api_client.put(
        "/api/access-password",
        json={"current_password": "eski-parol", "new_password": "yangi-parol"},
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 200
    assert await crud.verify_access_password(session, "yangi-parol") is True
    assert await crud.verify_access_password(session, "eski-parol") is False


async def test_notogri_joriy_parol_400(api_client, session, admin):
    await crud.create_initial_password(session, "eski-parol")

    response = await api_client.put(
        "/api/access-password",
        json={"current_password": "notogri", "new_password": "yangi-parol"},
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 400
    assert await crud.verify_access_password(session, "eski-parol") is True


async def test_hodim_parolni_ozgartira_olmaydi(api_client, session, employee):
    await crud.create_initial_password(session, "eski-parol")

    response = await api_client.put(
        "/api/access-password",
        json={"current_password": "eski-parol", "new_password": "yangi-parol"},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 403


async def test_qisqa_yangi_parol_rad_etiladi(api_client, session, admin):
    await crud.create_initial_password(session, "eski-parol")

    response = await api_client.put(
        "/api/access-password",
        json={"current_password": "eski-parol", "new_password": "abc"},
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 422


# ─── Hisobotlar ─────────────────────────────────────────────────────────────

async def test_hodim_faqat_ozinikini_koradi(
    api_client, session, employee, admin, districts
):
    await _report(session, employee, districts[0].id, customer="Meniki")
    await _report(session, admin, districts[0].id, customer="Boshqaniki")

    response = await api_client.get(
        "/api/reports", headers=auth_header(employee.telegram_id)
    )
    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["customer_name"] == "Meniki"


async def test_hodim_user_id_ni_almashtira_olmaydi(
    api_client, session, employee, admin, districts
):
    """So'rovdagi user_id ga ishonilmaydi — aks holda hodim boshqaning
    hisobotlarini o'qiy olardi."""
    await _report(session, admin, districts[0].id, customer="Boshqaniki")

    response = await api_client.get(
        f"/api/reports?user_id={admin.id}", headers=auth_header(employee.telegram_id)
    )

    assert response.json()["total"] == 0


async def test_admin_hammasini_koradi(api_client, session, employee, admin, districts):
    await _report(session, employee, districts[0].id)
    await _report(session, admin, districts[0].id)

    response = await api_client.get(
        "/api/reports", headers=auth_header(admin.telegram_id)
    )

    assert response.json()["total"] == 2


async def test_hodim_boshqaning_hisobotini_ocha_olmaydi(
    api_client, session, employee, admin, districts
):
    report = await _report(session, admin, districts[0].id)

    response = await api_client.get(
        f"/api/reports/{report.id}", headers=auth_header(employee.telegram_id)
    )

    assert response.status_code == 403


async def test_hisobot_yaratish(api_client, employee, districts):
    response = await api_client.post(
        "/api/reports",
        json={
            "report_type": "laboratory",
            "district_id": districts[0].id,
            "customer_name": "Yangi buyurtmachi",
            "lat": 41.31,
            "lon": 69.24,
            "plots_count": 5,
            "partner_ids": [],
            "photo_file_ids": ["a", "b", "c"],
        },
        headers=auth_header(employee.telegram_id),
    )
    body = response.json()

    assert response.status_code == 201
    assert body["status"] == "pending"
    assert body["author"]["id"] == employee.id
    assert body["plots_count"] == 5


async def test_kam_rasm_bilan_hisobot_rad_etiladi(api_client, employee, districts):
    response = await api_client.post(
        "/api/reports",
        json={
            "report_type": "visual",
            "district_id": districts[0].id,
            "customer_name": "Buyurtmachi",
            "lat": 41.31,
            "lon": 69.24,
            "photo_file_ids": ["a"],
        },
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 422


async def test_notogri_koordinata_rad_etiladi(api_client, employee, districts):
    response = await api_client.post(
        "/api/reports",
        json={
            "report_type": "visual",
            "district_id": districts[0].id,
            "customer_name": "Buyurtmachi",
            "lat": 200,
            "lon": 69.24,
            "photo_file_ids": ["a", "b", "c"],
        },
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 422


async def test_sherikka_bildirishnoma_ketadi(
    api_client, employee, admin, districts, fake_bot
):
    response = await api_client.post(
        "/api/reports",
        json={
            "report_type": "visual",
            "district_id": districts[0].id,
            "customer_name": "Buyurtmachi",
            "lat": 41.31,
            "lon": 69.24,
            "partner_ids": [admin.id],
            "photo_file_ids": ["a", "b", "c"],
        },
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 201
    assert fake_bot.media_groups, "sherikka rasmlar yuborilishi kerak edi"
    assert fake_bot.media_groups[0]["chat_id"] == admin.telegram_id


# ─── Tasdiqlash ─────────────────────────────────────────────────────────────

async def test_hodim_tasdiqlay_olmaydi(api_client, session, employee, districts):
    report = await _report(session, employee, districts[0].id)

    response = await api_client.post(
        f"/api/reports/{report.id}/approve", headers=auth_header(employee.telegram_id)
    )

    assert response.status_code == 403


async def test_admin_tasdiqlaydi_va_kanalga_ketadi(
    api_client, session, employee, admin, districts, fake_bot
):
    report = await _report(session, employee, districts[0].id)

    response = await api_client.post(
        f"/api/reports/{report.id}/approve", headers=auth_header(admin.telegram_id)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert fake_bot.media_groups, "kanalga yuborilishi kerak edi"


async def test_kanal_ishlamasa_tasdiqlanmaydi(
    api_client, session, employee, admin, districts, fake_bot
):
    """Kanalga bormagan hisobot tasdiqlangan deb belgilanmasligi kerak."""
    report = await _report(session, employee, districts[0].id)
    fake_bot.fail_on_send = True

    response = await api_client.post(
        f"/api/reports/{report.id}/approve", headers=auth_header(admin.telegram_id)
    )

    assert response.status_code == 502
    saqlangan = await crud.get_report_by_id(session, report.id)
    assert saqlangan.is_confirmed is False


async def test_ikki_marta_tasdiqlab_bolmaydi(
    api_client, session, employee, admin, districts
):
    report = await _report(session, employee, districts[0].id)

    birinchi = await api_client.post(
        f"/api/reports/{report.id}/approve", headers=auth_header(admin.telegram_id)
    )
    ikkinchi = await api_client.post(
        f"/api/reports/{report.id}/approve", headers=auth_header(admin.telegram_id)
    )

    assert birinchi.status_code == 200
    assert ikkinchi.status_code == 409


async def test_rad_etilgan_hisobot_saqlanadi(
    api_client, session, employee, admin, districts
):
    report = await _report(session, employee, districts[0].id)

    response = await api_client.post(
        f"/api/reports/{report.id}/reject", headers=auth_header(admin.telegram_id)
    )

    assert response.json()["status"] == "rejected"
    assert await crud.get_report_by_id(session, report.id) is not None


# ─── Hisobot bermaganlar ────────────────────────────────────────────────────

async def test_hodim_bermaganlar_royxatini_kora_olmaydi(api_client, employee):
    response = await api_client.get(
        "/api/reports/missing", headers=auth_header(employee.telegram_id)
    )

    assert response.status_code == 403


async def test_admin_bermaganlarni_koradi(api_client, employee, admin):
    response = await api_client.get(
        "/api/reports/missing", headers=auth_header(admin.telegram_id)
    )
    body = response.json()

    assert response.status_code == 200
    # Faqat hodim rolidagilar; admin o'zi ro'yxatga tushmaydi
    assert [u["id"] for u in body] == [employee.id]


async def test_hisobot_berganlar_royxatdan_chiqadi(
    api_client, session, employee, admin, districts
):
    await _report(session, employee, districts[0].id)

    response = await api_client.get(
        "/api/reports/missing", headers=auth_header(admin.telegram_id)
    )

    assert response.json() == []


async def test_missing_yol_report_id_bilan_toqnashmaydi(api_client, admin):
    """`/reports/missing` `/reports/{id}` dan oldin turishi kerak, aks holda
    "missing" so'zi id sifatida o'qilib 422 qaytarardi."""
    response = await api_client.get(
        "/api/reports/missing", headers=auth_header(admin.telegram_id)
    )

    assert response.status_code == 200


# ─── Excel eksport ──────────────────────────────────────────────────────────

async def test_admin_eksport_qiladi(api_client, session, employee, admin, districts, fake_bot):
    await _report(session, employee, districts[0].id)
    today = crud.local_today().isoformat()

    response = await api_client.post(
        "/api/reports/export",
        json={"date_from": today, "date_to": today},
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 200
    assert len(fake_bot.documents) == 1
    assert fake_bot.documents[0]["chat_id"] == admin.telegram_id


async def test_hodim_eksport_qila_olmaydi(api_client, admin, employee):
    today = crud.local_today().isoformat()

    response = await api_client.post(
        "/api/reports/export",
        json={"date_from": today, "date_to": today},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 403


async def test_bosh_oraliq_404(api_client, admin):
    today = crud.local_today().isoformat()

    response = await api_client.post(
        "/api/reports/export",
        json={"date_from": today, "date_to": today},
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 404


async def test_teskari_oraliq_400(api_client, admin):
    response = await api_client.post(
        "/api/reports/export",
        json={"date_from": "2026-06-10", "date_to": "2026-06-01"},
        headers=auth_header(admin.telegram_id),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "bad_range"


# ─── Rasm yuklash ───────────────────────────────────────────────────────────

async def test_rasm_yuklanadi_va_file_id_qaytadi(
    api_client, employee, fake_bot, monkeypatch
):
    monkeypatch.setattr(config, "STORAGE_CHAT_ID", -1001234567890)

    response = await api_client.post(
        "/api/photos",
        files={"file": ("rasm.jpg", b"\xff\xd8\xff-soxta-jpeg", "image/jpeg")},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 201
    assert response.json()["file_id"].startswith("file_")
    assert fake_bot.photos[0]["chat_id"] == -1001234567890


async def test_notogri_fayl_turi_rad_etiladi(api_client, employee, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_CHAT_ID", -1001234567890)

    response = await api_client.post(
        "/api/photos",
        files={"file": ("hujjat.pdf", b"%PDF-1.4", "application/pdf")},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 415


async def test_ombor_sozlanmagan_bolsa_503(api_client, employee, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_CHAT_ID", 0)

    response = await api_client.post(
        "/api/photos",
        files={"file": ("rasm.jpg", b"data", "image/jpeg")},
        headers=auth_header(employee.telegram_id),
    )

    assert response.status_code == 503
