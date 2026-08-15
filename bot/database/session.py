from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL

# pool_pre_ping: bot sutkalab ishlaydi va PostgreSQL qayta ishga tushsa yoki
# ulanishni uzib qo'ysa, eski ulanish bilan so'rov yuborilib xato bermasligi uchun.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def close_engine() -> None:
    await engine.dispose()
