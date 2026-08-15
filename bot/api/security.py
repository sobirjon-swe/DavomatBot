"""Telegram Mini App `initData` ni tekshirish.

Bu modul butun API ning ishonch nuqtasi. Mini App brauzerda ishlaydi,
ya'ni u yuborgan hamma narsani foydalanuvchi o'zgartira oladi. Yagona
himoya — Telegram bot tokeni bilan qo'ygan HMAC imzosi. Uni tekshirmasdan
`user.id` ga ishonish har kimga superadmin bo'lish imkonini beradi.

Alohida token (JWT) berilmaydi: har bir so'rovda initData qayta
tekshiriladi. HMAC hisobi mikrosoniyalar oladi, ammo o'g'irlanishi mumkin
bo'lgan uzoq muddatli token umuman paydo bo'lmaydi.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataError(Exception):
    """initData yaroqsiz yoki ishonchsiz."""


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""


@dataclass(frozen=True)
class InitData:
    user: TelegramUser
    auth_date: int


def _secret_key(bot_token: str) -> bytes:
    """Telegram hujjatidagi sxema: HMAC-SHA256("WebAppData", bot_token)."""
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _data_check_string(pairs: dict[str, str]) -> str:
    return "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))


def sign(pairs: dict[str, str], bot_token: str) -> str:
    """Berilgan maydonlar uchun imzo hisoblaydi (testlarda ham ishlatiladi)."""
    return hmac.new(
        _secret_key(bot_token), _data_check_string(pairs).encode(), hashlib.sha256
    ).hexdigest()


def parse_and_validate(
    init_data: str,
    bot_token: str,
    *,
    ttl_seconds: int,
    now: int | None = None,
) -> InitData:
    """initData ni tekshirib, ichidagi foydalanuvchini qaytaradi.

    Har qanday muammoda `InitDataError` ko'tariladi — chaqiruvchi uni
    401 ga aylantiradi va sababni foydalanuvchiga oshkor qilmaydi.
    """
    if not init_data:
        raise InitDataError("initData berilmagan")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise InitDataError("hash maydoni yo'q")

    # `signature` uchinchi tomon tekshiruvi uchun; u data_check_string ga
    # kirmaydi, shuning uchun hisobdan chiqariladi.
    pairs.pop("signature", None)

    expected = sign(pairs, bot_token)
    # compare_digest — vaqt bo'yicha hujumdan himoya
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("imzo mos kelmadi")

    raw_auth_date = pairs.get("auth_date", "")
    if not raw_auth_date.isdigit():
        raise InitDataError("auth_date yaroqsiz")

    auth_date = int(raw_auth_date)
    current = int(time.time()) if now is None else now

    if auth_date > current + 60:
        # Kelajakdagi sana — soat farqi yoki qalbakilashtirishga urinish
        raise InitDataError("auth_date kelajakda")
    if current - auth_date > ttl_seconds:
        raise InitDataError("initData muddati o'tgan")

    raw_user = pairs.get("user", "")
    if not raw_user:
        raise InitDataError("user maydoni yo'q")

    try:
        payload = json.loads(raw_user)
    except json.JSONDecodeError:
        raise InitDataError("user maydonini o'qib bo'lmadi") from None

    if not isinstance(payload, dict) or not isinstance(payload.get("id"), int):
        raise InitDataError("user.id yaroqsiz")
    if payload.get("is_bot"):
        raise InitDataError("bot hisobi qabul qilinmaydi")

    return InitData(
        user=TelegramUser(
            id=payload["id"],
            first_name=str(payload.get("first_name") or ""),
            last_name=str(payload.get("last_name") or ""),
            username=str(payload.get("username") or ""),
            language_code=str(payload.get("language_code") or ""),
        ),
        auth_date=auth_date,
    )
