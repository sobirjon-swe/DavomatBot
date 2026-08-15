
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from database.models import User, UserRole


class HasRole(BaseFilter):
    """Foydalanuvchi ko'rsatilgan rollardan biriga egaligini tekshiradi.

    `db_user` ni AuthMiddleware beradi. Filtr router darajasida qo'llanganda
    handlerlarning har biriga alohida tekshiruv yozish shart bo'lmaydi va,
    eng muhimi, inline tugma bosilganda ham ruxsat tekshiriladi — ilgari
    faqat menyu tugmasi bosilgandagina tekshirilardi.
    """

    def __init__(self, *roles: UserRole) -> None:
        self.roles = roles

    async def __call__(
        self, event: TelegramObject, db_user: User | None = None
    ) -> bool:
        return (
            db_user is not None
            and db_user.is_active
            and db_user.role in self.roles
        )


class IsAdmin(HasRole):
    def __init__(self) -> None:
        super().__init__(UserRole.admin, UserRole.superadmin)


class IsSuperAdmin(HasRole):
    def __init__(self) -> None:
        super().__init__(UserRole.superadmin)
