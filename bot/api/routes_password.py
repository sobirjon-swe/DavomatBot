import logging

from fastapi import APIRouter, HTTPException, status

from api.deps import AdminUser, SessionDep
from api.schemas import OkOut, PasswordChange
from database.crud import change_access_password, verify_access_password

logger = logging.getLogger(__name__)

router = APIRouter(tags=["password"])


@router.put("/access-password", response_model=OkOut)
async def change_password(
    payload: PasswordChange, admin: AdminUser, session: SessionDep
) -> OkOut:
    """Botga kirish uchun umumiy parolni almashtiradi.

    Bu shaxsiy hisob paroli emas — yangi hodim/admin ro'yxatdan o'tishda
    so'raladigan umumiy kirish paroli (botdagi "Parolni o'zgartirish" bilan
    bir xil parol, faqat shu yerda Mini App orqali ham o'zgartirish mumkin).
    """
    if not await verify_access_password(session, payload.current_password):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "wrong_current_password", "message": "Joriy parol noto'g'ri"},
        )

    await change_access_password(session, payload.new_password, admin.id)
    logger.info("Kirish paroli Mini App orqali o'zgartirildi (admin id=%s)", admin.id)
    return OkOut()
