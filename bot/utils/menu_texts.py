from locales import ru, uz

_MENU_BUTTON_KEYS = (
    "btn_report",
    "btn_settings",
    "btn_employees",
    "btn_reports",
    "btn_attendance",
    "btn_change_password",
    "btn_manage_roles",
)

RESERVED_MENU_TEXTS = frozenset(
    text
    for module in (uz, ru)
    for key in _MENU_BUTTON_KEYS
    if (text := getattr(module, key, None)) is not None
)
