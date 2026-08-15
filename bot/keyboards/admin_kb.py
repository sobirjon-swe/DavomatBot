from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from keyboards import webapp
from locales import t


def admin_login_choice_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_login_as_employee"), callback_data="admin_login:employee")
    builder.button(text=t(lang, "btn_login_as_admin"), callback_data="admin_login:admin")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_menu_kb(lang: str, is_superadmin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=t(lang, "btn_employees"))
    builder.button(text=t(lang, "btn_reports"))
    builder.button(text=t(lang, "btn_attendance"))
    builder.button(text=t(lang, "btn_change_password"))
    builder.button(text=t(lang, "btn_settings"))
    if is_superadmin:
        builder.button(text=t(lang, "btn_manage_roles"))

    app_button = webapp.reply_button(lang)
    if app_button is not None:
        builder.add(app_button)
        # Ro'yxatlar bilan ishlash ilovada qulayroq — tugma alohida,
        # ko'rinadigan qatorda turadi.
        builder.adjust(2, 2, 2, 1)
    else:
        builder.adjust(2)

    return builder.as_markup(resize_keyboard=True)


def employees_section_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_list_employees"), callback_data="emp:list")
    builder.button(text=t(lang, "btn_add_employee"), callback_data="emp:add")
    builder.adjust(1)
    return builder.as_markup()


def employee_actions_kb(
    lang: str,
    user_id: int,
    is_superadmin: bool = False,
    is_active: bool = True,
) -> InlineKeyboardMarkup:
    """Hodim kartochkasi tugmalari.

    Faolsizlantirish/tiklash faqat superadminga ko'rsatiladi — ilgari
    `is_superadmin` qabul qilinardi-yu, e'tiborga olinmasdi.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_edit"), callback_data=f"emp_edit:{user_id}")
    if is_superadmin:
        if is_active:
            builder.button(
                text=t(lang, "btn_deactivate"), callback_data=f"emp_off:{user_id}"
            )
        else:
            builder.button(
                text=t(lang, "btn_activate"), callback_data=f"emp_on:{user_id}"
            )
    builder.adjust(2)
    return builder.as_markup()


def confirm_deactivate_kb(lang: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t(lang, "btn_yes_deactivate"),
        callback_data=f"emp_off_confirm:{user_id}",
    )
    builder.button(text=t(lang, "btn_cancel"), callback_data="emp_off_cancel")
    builder.adjust(2)
    return builder.as_markup()


def edit_employee_menu_kb(lang: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, key in (
        ("name", "btn_edit_name"),
        ("position", "btn_edit_position"),
        ("districts", "btn_edit_districts"),
    ):
        builder.button(text=t(lang, key), callback_data=f"emp_edit_field:{user_id}:{field}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb(lang: str, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_confirm"), callback_data=f"confirm:{action}")
    builder.button(text=t(lang, "btn_cancel"), callback_data="confirm:cancel")
    builder.adjust(2)
    return builder.as_markup()


def reports_section_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_today_reports"), callback_data="rpt:today")
    builder.button(text=t(lang, "btn_missing"), callback_data="rpt:missing")
    builder.button(text=t(lang, "btn_search_reports"), callback_data="rpt:search")
    builder.button(text=t(lang, "btn_export"), callback_data="rpt:export")
    builder.adjust(1)
    return builder.as_markup()


def export_range_kb(lang: str) -> InlineKeyboardMarkup:
    """Eksport uchun tayyor oraliqlar — ko'p hollarda sana yozish shart emas."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_range_today"), callback_data="exp:today")
    builder.button(text=t(lang, "btn_range_week"), callback_data="exp:week")
    builder.button(text=t(lang, "btn_range_month"), callback_data="exp:month")
    builder.button(text=t(lang, "btn_range_custom"), callback_data="exp:custom")
    builder.adjust(3, 1)
    return builder.as_markup()


def view_photos_kb(lang: str, report_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_view_photos"), callback_data=f"rpt_photos:{report_id}")
    builder.adjust(1)
    return builder.as_markup()


def attendance_approve_kb(lang: str, report_id: int, page: int = 1) -> InlineKeyboardMarkup:
    """Tasdiqlash/rad etish tugmalari.

    Sahifa raqami callback ichida yuriladi, shunda amaldan keyin admin
    ro'yxatning o'sha joyida qoladi.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_approve"), callback_data=f"att_approve:{report_id}:{page}")
    builder.button(text=t(lang, "btn_reject"), callback_data=f"att_reject:{report_id}:{page}")
    if page:
        builder.button(text=t(lang, "btn_view_photos"), callback_data=f"rpt_photos:{report_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def employees_list_kb(lang: str, employees: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for emp in employees:
        builder.button(text=emp.full_name, callback_data=f"sel_emp:{emp.id}")
    builder.adjust(1)
    return builder.as_markup()


def role_choice_kb(lang: str, current_role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_role != "admin":
        builder.button(text=t(lang, "btn_make_admin"), callback_data="role:admin")
    if current_role != "employee":
        builder.button(text=t(lang, "btn_make_employee"), callback_data="role:employee")
    builder.button(text=t(lang, "btn_cancel"), callback_data="role:cancel")
    builder.adjust(1)
    return builder.as_markup()


def back_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_back"), callback_data="back")
    builder.adjust(1)
    return builder.as_markup()
