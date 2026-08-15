from typing import Optional

from aiogram.types import Message


def text_of(message: Message) -> Optional[str]:
    """Xabardan matnni oladi; matn bo'lmasa (rasm, stiker, ovoz) None.

    Matn kutayotgan handlerlar ilgari `message.text.strip()` deb yozar va
    foydalanuvchi rasm yuborsa AttributeError bilan yiqilardi.
    """
    return message.text.strip() if message.text else None
