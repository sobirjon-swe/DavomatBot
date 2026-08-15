import os

# Bot modullarini import qilishdan OLDIN sozlamalar qo'yilishi kerak:
# config.py import paytida o'qiydi, database/session.py esa engine yaratadi.
# Ataylab setdefault emas — ishlab chiquvchining .env yoki shell qiymatlari
# testga sizib kirmasligi uchun.
os.environ["BOT_TOKEN"] = "123456:TEST-TOKEN"
os.environ["SUPERADMIN_ID"] = "1"
os.environ["CHANNEL_ID"] = "-1001234567890"
os.environ["REDIS_URL"] = ""

# Standart holatda testlar xotiradagi SQLite da ishlaydi — tez va hech narsa
# talab qilmaydi. TEST_DATABASE_URL berilsa (CI da) haqiqiy PostgreSQL
# ishlatiladi; faqat o'shanda vaqt mintaqali ustunlar to'liq sinaladi.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
IS_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import json  # noqa: E402
import time  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from urllib.parse import urlencode  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

import config  # noqa: E402
from api.security import sign  # noqa: E402
from database.crud import create_user, get_all_districts, seed_districts  # noqa: E402
from database.models import Base, UserRole  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """SQLite da ishlaganda PostgreSQL talab qiladigan testlarni o'tkazib yuborish."""
    if IS_POSTGRES:
        return
    skip = pytest.mark.skip(
        reason="SQLite vaqt mintaqasini saqlamaydi; TEST_DATABASE_URL bilan PostgreSQL kerak"
    )
    for item in items:
        if "requires_pg" in item.keywords:
            item.add_marker(skip)


@pytest_asyncio.fixture
async def session():
    """Har bir test uchun toza baza."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        # PostgreSQL da baza testlar orasida saqlanib qoladi, shuning uchun
        # avval tozalanadi. SQLite xotirada bo'lgani uchun baribir bo'sh.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def districts(session):
    await seed_districts(session)
    return await get_all_districts(session)


@pytest_asyncio.fixture
async def employee(session):
    return await create_user(
        session,
        full_name="Ali Valiyev",
        position="Muhandis",
        language="uz",
        telegram_id=500001,
    )


@pytest_asyncio.fixture
async def admin(session):
    return await create_user(
        session,
        full_name="Salim Adminov",
        position="Boshliq",
        language="uz",
        telegram_id=500002,
        role=UserRole.admin,
    )


@pytest_asyncio.fixture
async def superadmin(session):
    return await create_user(
        session,
        full_name="Sardor Superadminov",
        position="Rahbar",
        language="uz",
        telegram_id=500003,
        role=UserRole.superadmin,
    )


# ─── Mini App API ───────────────────────────────────────────────────────────

def make_init_data(
    telegram_id: int,
    *,
    bot_token: str | None = None,
    auth_date: int | None = None,
    tamper_user_id: int | None = None,
) -> str:
    """Haqiqiy imzoli initData yasaydi.

    `tamper_user_id` berilsa, imzo qo'yilgandan KEYIN user.id almashtiriladi —
    imzo tekshiruvi ishlayotganini shu bilan sinaymiz.
    """
    token = bot_token or config.BOT_TOKEN
    user_json = json.dumps(
        {"id": telegram_id, "first_name": "Test", "language_code": "uz"},
        separators=(",", ":"),
    )
    pairs = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAHtest",
        "user": user_json,
    }
    pairs["hash"] = sign({k: v for k, v in pairs.items()}, token)

    if tamper_user_id is not None:
        pairs["user"] = json.dumps(
            {"id": tamper_user_id, "first_name": "Test", "language_code": "uz"},
            separators=(",", ":"),
        )

    return urlencode(pairs)


def auth_header(telegram_id: int, **kwargs) -> dict[str, str]:
    return {"Authorization": f"tma {make_init_data(telegram_id, **kwargs)}"}


class FakeBot:
    """Telegram ga chiqmaydigan bot o'rnini bosuvchi.

    Yuborilgan xabarlarni yozib boradi, shunda testlar sherikka
    bildirishnoma ketgan-ketmaganini tekshira oladi.
    """

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.photos: list[dict] = []
        self.media_groups: list[dict] = []
        self.fail_on_send = False

    async def send_message(self, chat_id, text, **kwargs):
        if self.fail_on_send:
            raise RuntimeError("Telegram xatosi")
        self.messages.append({"chat_id": chat_id, "text": text})
        return SimpleNamespace(message_id=len(self.messages))

    async def send_photo(self, chat_id, photo, **kwargs):
        if self.fail_on_send:
            raise RuntimeError("Telegram xatosi")
        self.photos.append({"chat_id": chat_id, "photo": photo})
        return SimpleNamespace(
            message_id=len(self.photos),
            photo=[SimpleNamespace(file_id=f"file_{len(self.photos)}")],
        )

    async def send_media_group(self, chat_id, media, **kwargs):
        if self.fail_on_send:
            raise RuntimeError("Telegram xatosi")
        self.media_groups.append({"chat_id": chat_id, "media": media})
        return []


@pytest.fixture
def fake_bot() -> FakeBot:
    return FakeBot()


@pytest.fixture
def session_factory(session):
    """Fon vazifalari uchun sessiya manbasi.

    Ular odatda AsyncSessionLocal ni chaqiradi, lekin u testdagi
    xotira bazasiga emas, boshqa ulanishga borib qoladi.
    """

    @asynccontextmanager
    async def factory():
        yield session

    return factory


@pytest_asyncio.fixture
async def api_client(session, fake_bot):
    """Tarmoqqa chiqmasdan FastAPI ilovasini chaqiradigan mijoz."""
    from api.app import app
    from api.deps import get_bot, get_session

    async def _session_override():
        yield session

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_bot] = lambda: fake_bot

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
