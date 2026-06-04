from locales import uz, ru


def t(lang: str, key: str, **kwargs) -> str:
    module = uz if lang == "uz" else ru
    text = getattr(module, key, key)
    return text.format(**kwargs) if kwargs else text
