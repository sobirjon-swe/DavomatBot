# ─── Общее ──────────────────────────────────────────────────────────────────
choose_language = "🌐 Выберите язык:"
btn_uz = "🇺🇿 O'zbek"
btn_ru = "🇷🇺 Русский"

enter_password = "🔑 Введите пароль для входа:"
wrong_password = "❌ Неверный пароль. Попробуйте снова. ({attempts}/3)"
account_blocked = "⛔ Вы заблокированы. Обратитесь к администратору."
account_deactivated = "⛔ Ваша учётная запись деактивирована. Обратитесь к администратору."

text_expected = "✍️ Пожалуйста, отправьте текстом."
location_expected = "📍 Пожалуйста, отправьте местоположение через кнопку."
invalid_number = "🔢 Введите только число."
action_cancelled = "❌ Действие отменено."
nothing_to_cancel = "ℹ️ Нечего отменять."

# ─── Постраничный вывод ──────────────────────────────────────────────────────
btn_back_to_list = "◀️ К списку"
employees_list_header = "👥 <b>Сотрудники</b> — всего {total}"
reports_list_header = "📊 <b>Отчёты</b> — всего {total}"
pending_list_header = "✅ <b>Ожидают подтверждения</b> — всего {total}"

# ─── Регистрация ─────────────────────────────────────────────────────────────
enter_full_name = "👤 Введите ваше имя и фамилию:"
enter_position = "💼 Введите вашу должность:"
choose_districts = "🗺 Выберите назначенные вам районы:\n(Можно выбрать несколько)"
no_districts_selected = "⚠️ Выберите хотя бы один район."
choose_your_record = (
    "👤 Найдите себя в списке:\n"
    "(Администратор мог добавить вас заранее)"
)
btn_not_in_list = "➕ Меня нет в списке"
record_already_taken = "⚠️ Эта запись уже занята. Выберите другую."
registration_complete = (
    "✅ Вы зарегистрированы!\n\n"
    "👤 Имя: {full_name}\n"
    "💼 Должность: {position}\n"
    "🗺 Районы: {districts}"
)
new_employee_notify = (
    "🆕 Новый сотрудник зарегистрировался:\n\n"
    "👤 {full_name}\n"
    "💼 {position}\n"
    "🗺 Районы: {districts}"
)

# ─── Главное меню ────────────────────────────────────────────────────────────
main_menu = "📌 Главное меню"
btn_report = "📋 Подать отчёт"
btn_settings = "⚙️ Настройки"

# ─── Mini App ────────────────────────────────────────────────────────────────
btn_open_app = "📱 Открыть приложение"
menu_button_app = "Davomat"

# ─── Настройки ───────────────────────────────────────────────────────────────
settings_menu = "⚙️ Настройки"
btn_edit_districts = "📍 Изменить районы"
btn_change_language = "🌐 Изменить язык"
districts_updated = "✅ Районы обновлены."
language_changed = "✅ Язык изменён."

# ─── Отчёт ───────────────────────────────────────────────────────────────────
choose_report_type = "📋 Тип отчёта:"
btn_laboratory = "🔬 Лаборатория"
btn_technical = "🔍 Технический осмотр"
btn_visual = "👁 Визуальный осмотр"
btn_instrumental = "🔧 Инструментальный осмотр"

choose_partners = "🤝 Партнёры (необязательно):\n(Можно выбрать несколько)"
btn_no_partner = "👤 Без партнёра"
btn_continue = "▶️ Продолжить"

choose_district = "🗺 Выберите район:"
btn_other_district = "🔍 Другой район"
enter_customer = "🏢 Введите название заказчика:"
send_location = "📍 Отправьте ваше местоположение:"
btn_send_location = "📍 Отправить местоположение"
send_photos = "📸 Отправьте фотографии ({min}-{max} шт.):"
photos_progress = "📸 Отправлено фото: {count} (нужно минимум {min})"
btn_done = "✅ Готово"
min_photos_required = "📸 Необходимо отправить минимум {min} фотографии."
max_photos_reached = "📸 Можно отправить не более {max} фотографий."
enter_plots_count = "🔢 Введите количество участков или пропустите:"
btn_skip = "⏭ Пропустить"

report_preview = (
    "📋 <b>Проверьте ваш отчёт:</b>\n\n"
    "🏗 Тип: {report_type}\n"
    "📍 Район: {district}\n"
    "🏢 Заказчик: {customer}\n"
    "🤝 Партнёры: {partners}\n"
    "📸 Фото: {photos_count} шт.\n"
    "🗓 Дата: {date}\n"
    "🗺 Местоположение: {location}"
)
report_preview_plots = "\n🔢 Участки: {plots_count}"
btn_submit = "✅ Отправить"
btn_refill = "✏️ Заполнить заново"

report_submitted = "✅ Ваш отчёт принят!\nОжидайте подтверждения администратора."
report_cancelled = "❌ Отчёт отменён."
report_approved_notify = "✅ Ваш отчёт подтверждён и отправлен в канал."
report_rejected_notify = (
    "❌ Ваш отчёт отклонён. За подробностями обратитесь к администратору."
)

partner_notified = (
    "📋 <b>{sender}</b> добавил(а) вас как партнёра в сегодняшний отчёт.\n\n"
    "👤 Сотрудник: {sender}\n"
    "💼 Должность: {position}\n"
    "🏗 Тип: {report_type}\n"
    "📍 Район: {district}\n"
    "🏢 Заказчик: {customer}\n"
    "🤝 Партнёры: {partners}\n"
    "🗓 Дата: {date}"
)

# ─── Типы отчётов (текст) ─────────────────────────────────────────────────────
type_laboratory = "Лаборатория"
type_visual = "Визуальный осмотр"
type_instrumental = "Инструментальный осмотр"

# ─── Выбор роли при входе ────────────────────────────────────────────────────
admin_login_choice = "👋 Добро пожаловать!\n\nКак вы хотите войти?"
btn_login_as_employee = "👤 Как сотрудник"
btn_login_as_admin = "🔐 Как администратор"

# ─── Меню администратора ─────────────────────────────────────────────────────
admin_menu = "🔐 Панель администратора"
btn_employees = "👥 Сотрудники"
btn_reports = "📊 Отчёты"
btn_attendance = "✅ Подтверждение посещаемости"
btn_change_password = "🔑 Изменить пароль"
btn_manage_roles = "👑 Изменить роли"
btn_back = "◀️ Назад"

# ─── Раздел сотрудников ──────────────────────────────────────────────────────
employees_menu = "👥 Раздел сотрудников"
btn_list_employees = "📋 Список сотрудников"
btn_add_employee = "➕ Добавить сотрудника"
no_employees = "👥 Пока нет сотрудников."

employee_card = (
    "👤 <b>{full_name}</b>\n"
    "💼 {position}\n"
    "🔑 Роль: {role}\n"
    "🗺 Районы: {districts}\n"
    "📅 Добавлен: {created_at}\n"
    "📌 Статус: {status}"
)
status_active = "активен"
status_inactive = "деактивирован"

btn_edit = "✏️ Изменить"
btn_deactivate = "🚫 Деактивировать"
btn_activate = "♻️ Восстановить"
btn_yes_deactivate = "✅ Да, деактивировать"
confirm_deactivate = (
    "⚠️ Деактивировать сотрудника?\n\n"
    "👤 {full_name}\n\n"
    "Его отчёты сохранятся, но он не сможет пользоваться ботом."
)
employee_deactivated = "✅ Сотрудник деактивирован."
employee_activated = "✅ Сотрудник восстановлен."
cannot_deactivate_self = "⚠️ Нельзя деактивировать самого себя."
btn_cancel = "❌ Отмена"
employee_not_found = "❌ Сотрудник не найден."

add_employee_name = "👤 Введите имя нового сотрудника:"
add_employee_position = "💼 Введите его должность:"
add_employee_districts = "🗺 Выберите его районы:"
employee_added = (
    "✅ Сотрудник добавлен:\n👤 {full_name}\n💼 {position}\n\n"
    "При первом входе в бот через /start он выберет свою запись."
)

edit_employee_menu = "✏️ Что хотите изменить?"
btn_edit_name = "👤 Имя"
btn_edit_position = "💼 Должность"
enter_new_name = "👤 Введите новое имя:"
enter_new_position = "💼 Введите новую должность:"
employee_updated = "✅ Данные обновлены."

confirm_action = "✅ Подтвердить"
btn_confirm = "✅ Подтвердить"

# ─── Раздел отчётов ──────────────────────────────────────────────────────────
reports_menu = "📊 Отчёты"
btn_today_reports = "📅 Отчёты за сегодня"
btn_search_reports = "🔍 Поиск"
no_reports = "📭 Отчёты не найдены."
no_photos = "📭 Фотографии не найдены."

search_date = "📅 Введите дату (например: 05.06.2026):"
search_employee = "👤 Выберите сотрудника:"
invalid_date = "❌ Неверный формат даты. Например: 05.06.2026"

report_card = (
    "👤 <b>{full_name}</b>\n"
    "💼 {position}\n"
    "🏗 {report_type}\n"
    "📍 {district}\n"
    "🏢 {customer}\n"
    "🤝 Партнёры: {partners}\n"
    "🗓 {date}\n"
    "🗺 Местоположение: {location}"
)
btn_view_photos = "📸 Просмотр фото"

# ─── Подтверждение посещаемости ──────────────────────────────────────────────
attendance_menu = "✅ Ожидают подтверждения"
no_pending = "✅ Нет неподтверждённых отчётов."
btn_approve = "✅ Подтвердить"
btn_reject = "❌ Отклонить"
report_approved = "✅ Отчёт подтверждён и отправлен в канал."
report_rejected = "❌ Отчёт отклонён."
report_not_found = "❌ Отчёт не найден."
report_already_processed = "ℹ️ Этот отчёт уже обработан."
report_not_approved = "❌ Отчёт не подтверждён."
channel_send_failed = "❌ Ошибка при отправке в канал:\n<code>{error}</code>"

channel_report = (
    "✅ <b>Посещаемость подтверждена</b>\n\n"
    "👤 Сотрудник: {full_name}\n"
    "💼 Должность: {position}\n"
    "🏗 Тип: {report_type}\n"
    "📍 Район: {district}\n"
    "🏢 Заказчик: {customer}\n"
    "🤝 Партнёры: {partners}\n"
    "🗓 Дата: {date}\n"
    "🗺 Местоположение: {location}"
)

# ─── Смена пароля ────────────────────────────────────────────────────────────
enter_current_password = "🔑 Введите текущий пароль:"
enter_new_password = "🔑 Введите новый пароль (минимум {min} символов):"
enter_confirm_password = "🔑 Повторите новый пароль:"
passwords_mismatch = "❌ Пароли не совпадают."
password_too_short = "❌ Пароль должен содержать минимум {min} символов."
password_changed = "✅ Пароль успешно изменён."
wrong_current_password = "❌ Текущий пароль неверный."

# ─── Управление ролями ───────────────────────────────────────────────────────
roles_menu = "👑 Изменение ролей"
choose_employee_for_role = "👤 Выберите сотрудника:"
choose_new_role = "🔑 Выберите новую роль:\n\n👤 {full_name} - текущая роль: {current_role}"
btn_make_admin = "👑 Назначить администратором"
btn_make_employee = "👤 Вернуть как сотрудника"
role_updated = "✅ Роль {full_name} изменена: {new_role}"
role_update_confirm = "👤 {full_name}\n📌 Новая роль: {new_role}\n\nПодтвердить?"

admin_assigned_notify = "🎉 Вы назначены администратором!"
admin_removed_notify = "📌 Ваши права администратора отозваны."

# ─── Ошибки ──────────────────────────────────────────────────────────────────
error_generic = "❌ Произошла ошибка. Попробуйте снова."
not_authorized = "⛔ У вас нет прав для этого действия."
