"""Kirish parolini qo'lda o'rnatish uchun yordamchi skript.

Ishlatish (bot/ katalogidan):
    python reset_password.py "yangi-parol"
    python reset_password.py            # tasodifiy parol yaratadi

Ilgari bu faylda parol kodning ichida yozib qo'yilgan edi va u ishga
tushirilishi bilan hech qanday tekshiruvsiz almashardi.
"""
import asyncio
import secrets
import string
import sys

import config
from database.crud import change_access_password
from database.session import AsyncSessionLocal, close_engine


def _generate(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def main() -> int:
    config.validate()

    if len(sys.argv) > 2:
        print("Ishlatish: python reset_password.py [yangi-parol]")
        return 2

    password = sys.argv[1] if len(sys.argv) == 2 else _generate()

    if len(password) < config.MIN_PASSWORD_LENGTH:
        print(
            f"Parol kamida {config.MIN_PASSWORD_LENGTH} ta belgidan "
            f"iborat bo'lishi kerak."
        )
        return 1

    try:
        async with AsyncSessionLocal() as session:
            # created_by=None: parol odam emas, skript orqali o'zgartirildi.
            await change_access_password(session, password, created_by=None)
    finally:
        await close_engine()

    print(f"Yangi kirish paroli o'rnatildi: {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
