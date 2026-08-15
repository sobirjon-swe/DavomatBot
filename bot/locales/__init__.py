import logging

from locales import ru, uz

logger = logging.getLogger(__name__)

_MODULES = {"uz": uz, "ru": ru}


def t(lang: str, key: str, **kwargs) -> str:
    """Kalit bo'yicha tarjimani qaytaradi.

    Tarjima topilmasa o'zbekchaga qaytadi va logga ogohlantirish yozadi —
    ilgari kalitning o'zi foydalanuvchiga ko'rinib qolardi.
    """
    module = _MODULES.get(lang, uz)
    text = getattr(module, key, None)

    if text is None:
        text = getattr(uz, key, None)
        if text is None:
            logger.warning("Tarjima kaliti topilmadi: %s (%s)", key, lang)
            return key
        logger.warning("'%s' kaliti %s tilida yo'q, uz ishlatildi", key, lang)

    if not kwargs:
        return text

    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        logger.warning("Tarjimani formatlashda xato: %s (%s)", key, lang)
        return text
