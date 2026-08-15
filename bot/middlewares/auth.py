from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.crud import get_user_by_telegram_id
from database.session import AsyncSessionLocal


class AuthMiddleware(BaseMiddleware):
    """Har bir yangilanish uchun foydalanuvchini bazadan bir marta o'qiydi.

    Natija `db_user` nomi bilan handler va filtrlarga uzatiladi. Shu sababli
    handlerlar `get_user_by_telegram_id` ni qayta chaqirmaydi va rolga
    asoslangan filtrlar ishlay oladi.

    Sessiya handlerga uzatilmaydi: handlerlar ichida uzoq davom etadigan
    Telegram so'rovlari bor va bazaga ulanish shuncha vaqt band bo'lib
    turmasligi kerak. Yuklab olingan obyekt (tumanlari bilan birga)
    sessiya yopilgach ham o'qishga yaroqli.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user") or getattr(event, "from_user", None)

        db_user = None
        if tg_user is not None and not tg_user.is_bot:
            async with AsyncSessionLocal() as session:
                db_user = await get_user_by_telegram_id(session, tg_user.id)

        data["db_user"] = db_user
        return await handler(event, data)
