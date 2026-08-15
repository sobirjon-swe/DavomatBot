import logging
from collections.abc import AsyncIterator
from typing import Annotated

from aiogram import Bot
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import config
from api.security import InitDataError, parse_and_validate
from database.crud import get_user_by_telegram_id
from database.models import User, UserRole
from database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    """Rasm yuklash va kanalga chiqarish uchun bot mijozi.

    Bir marta yaratiladi; jarayon tugaganda `close_bot` uni yopadi.
    """
    global _bot
    if _bot is None:
        _bot = Bot(token=config.BOT_TOKEN)
    return _bot


async def close_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
BotDep = Annotated[Bot, Depends(get_bot)]


def _extract_init_data(authorization: str | None) -> str:
    """`Authorization: tma <initData>` sarlavhasidan initData ni ajratadi."""
    if not authorization:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Avtorizatsiya talab qilinadi"},
        )

    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "tma" or not value.strip():
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Avtorizatsiya sxemasi noto'g'ri"},
        )
    return value.strip()


async def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    raw = _extract_init_data(authorization)

    try:
        data = parse_and_validate(
            raw, config.BOT_TOKEN, ttl_seconds=config.INITDATA_TTL_SECONDS
        )
    except InitDataError as exc:
        # Sabab logga yoziladi, lekin javobda oshkor qilinmaydi — aks holda
        # imzoni tanlab olishga urinayotgan odamga yordam bergan bo'lardik.
        logger.warning("initData rad etildi: %s", exc)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Avtorizatsiya ma'lumoti yaroqsiz"},
        ) from None

    user = await get_user_by_telegram_id(session, data.user.id)

    if user is None:
        # Frontend bu kodni ko'rib foydalanuvchini botga yo'naltiradi.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "not_registered",
                "message": "Avval botda ro'yxatdan o'ting",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "deactivated",
                "message": "Hisobingiz faolsizlantirilgan",
            },
        )

    return user


CurrentUser = Annotated[User, Depends(current_user)]


def _forbidden() -> HTTPException:
    return HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={"code": "forbidden", "message": "Ruxsat yo'q"},
    )


async def require_admin(user: CurrentUser) -> User:
    if user.role not in (UserRole.admin, UserRole.superadmin):
        raise _forbidden()
    return user


async def require_superadmin(user: CurrentUser) -> User:
    if user.role != UserRole.superadmin:
        raise _forbidden()
    return user


AdminUser = Annotated[User, Depends(require_admin)]
SuperAdminUser = Annotated[User, Depends(require_superadmin)]
