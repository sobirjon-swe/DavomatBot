from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
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
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def employees_section_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_list_employees"), callback_data="emp:list")
    builder.button(text=t(lang, "btn_add_employee"), callback_data="emp:add")
    builder.adjust(1)
    return builder.as_markup()


def employee_actions_kb(lang: str, user_id: int, is_superadmin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_edit"), callback_data=f"emp_edit:{user_id}")
    builder.button(text=t(lang, "btn_delete"), callback_data=f"emp_del:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_delete_kb(lang: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_yes_delete"), callback_data=f"emp_del_confirm:{user_id}")
    builder.button(text=t(lang, "btn_cancel"), callback_data="emp_del_cancel")
    builder.adjust(2)
    return builder.as_markup()


def edit_employee_menu_kb(lang: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_edit_name"), callback_data=f"emp_edit_field:{user_id}:name")
    builder.button(text=t(lang, "btn_edit_position"), callback_data=f"emp_edit_field:{user_id}:position")
    builder.button(text=t(lang, "btn_edit_districts"), callback_data=f"emp_edit_field:{user_id}:districts")
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
    builder.button(text=t(lang, "btn_search_reports"), callback_data="rpt:search")
    builder.adjust(1)
    return builder.as_markup()


def view_photos_kb(lang: str, report_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_view_photos"), callback_data=f"rpt_photos:{report_id}")
    builder.adjust(1)
    return builder.as_markup()


def attendance_approve_kb(lang: str, report_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "btn_approve"), callback_data=f"att_approve:{report_id}")
    builder.button(text=t(lang, "btn_reject"), callback_data=f"att_reject:{report_id}")
    builder.adjust(2)
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
