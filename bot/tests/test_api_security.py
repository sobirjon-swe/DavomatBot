"""initData tekshiruvi — API ning yagona ishonch nuqtasi.

Bu testlar buzilsa, har kim o'zini boshqa foydalanuvchi qilib ko'rsata oladi.
"""
import json
import time
from urllib.parse import urlencode

import pytest

from api.security import InitDataError, parse_and_validate, sign

TOKEN = "123456:TEST-TOKEN"
BOSHQA_TOKEN = "999999:OTHER-TOKEN"


def _init_data(
    *,
    user: dict | None = None,
    auth_date: int | None = None,
    token: str = TOKEN,
    extra: dict | None = None,
) -> str:
    pairs = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAHtest",
        "user": json.dumps(user or {"id": 42, "first_name": "Ali"}, separators=(",", ":")),
    }
    if extra:
        pairs.update(extra)
    pairs["hash"] = sign(dict(pairs), token)
    return urlencode(pairs)


def _parse(raw: str, *, ttl: int = 3600, now: int | None = None):
    return parse_and_validate(raw, TOKEN, ttl_seconds=ttl, now=now)


# ─── To'g'ri holat ──────────────────────────────────────────────────────────

def test_togri_imzo_qabul_qilinadi():
    data = _parse(_init_data(user={"id": 777, "first_name": "Ali", "language_code": "uz"}))

    assert data.user.id == 777
    assert data.user.first_name == "Ali"
    assert data.user.language_code == "uz"


def test_qoshimcha_maydonlar_imzoga_kiradi():
    """Telegram yangi maydon qo'shsa ham tekshiruv ishlashi kerak."""
    raw = _init_data(extra={"chat_type": "private", "start_param": "abc"})

    assert _parse(raw).user.id == 42


def test_signature_maydoni_hisobga_olinmaydi():
    """`signature` uchinchi tomon tekshiruvi uchun va data_check_string ga kirmaydi."""
    raw = _init_data() + "&signature=" + "a" * 64

    assert _parse(raw).user.id == 42


# ─── Qalbakilashtirishga urinishlar ─────────────────────────────────────────

def test_user_id_almashtirilsa_rad_etiladi():
    """Eng muhim test: imzodan keyin user.id ni o'zgartirish."""
    raw = _init_data(user={"id": 42, "first_name": "Ali"})
    buzilgan = raw.replace("42", "1", 1)

    with pytest.raises(InitDataError):
        _parse(buzilgan)


def test_boshqa_token_bilan_imzolangani_rad_etiladi():
    raw = _init_data(token=BOSHQA_TOKEN)

    with pytest.raises(InitDataError):
        _parse(raw)


def test_hash_siz_rad_etiladi():
    pairs = {"auth_date": str(int(time.time())), "user": '{"id":42}'}

    with pytest.raises(InitDataError):
        _parse(urlencode(pairs))


def test_bosh_initdata_rad_etiladi():
    with pytest.raises(InitDataError):
        _parse("")


def test_tasodifiy_matn_rad_etiladi():
    with pytest.raises(InitDataError):
        _parse("bu-umuman-initdata-emas")


# ─── Muddat ─────────────────────────────────────────────────────────────────

def test_eski_initdata_rad_etiladi():
    hozir = 1_800_000_000
    raw = _init_data(auth_date=hozir - 7200)

    with pytest.raises(InitDataError):
        _parse(raw, ttl=3600, now=hozir)


def test_muddat_ichidagi_initdata_qabul_qilinadi():
    hozir = 1_800_000_000
    raw = _init_data(auth_date=hozir - 60)

    assert _parse(raw, ttl=3600, now=hozir).user.id == 42


def test_kelajakdagi_auth_date_rad_etiladi():
    """Soat farqi uchun 60 soniya beriladi, undan ortig'i shubhali."""
    hozir = 1_800_000_000
    raw = _init_data(auth_date=hozir + 600)

    with pytest.raises(InitDataError):
        _parse(raw, now=hozir)


def test_raqam_bolmagan_auth_date_rad_etiladi():
    pairs = {"auth_date": "kecha", "user": '{"id":42}'}
    pairs["hash"] = sign(dict(pairs), TOKEN)

    with pytest.raises(InitDataError):
        _parse(urlencode(pairs))


# ─── user maydoni ───────────────────────────────────────────────────────────

def test_user_siz_rad_etiladi():
    pairs = {"auth_date": str(int(time.time())), "query_id": "AAH"}
    pairs["hash"] = sign(dict(pairs), TOKEN)

    with pytest.raises(InitDataError):
        _parse(urlencode(pairs))


def test_buzuq_json_rad_etiladi():
    pairs = {"auth_date": str(int(time.time())), "user": "{buzuq"}
    pairs["hash"] = sign(dict(pairs), TOKEN)

    with pytest.raises(InitDataError):
        _parse(urlencode(pairs))


def test_matnli_id_rad_etiladi():
    with pytest.raises(InitDataError):
        _parse(_init_data(user={"id": "42", "first_name": "Ali"}))


def test_bot_hisobi_rad_etiladi():
    with pytest.raises(InitDataError):
        _parse(_init_data(user={"id": 42, "first_name": "Bot", "is_bot": True}))
