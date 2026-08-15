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

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

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
