# ─── Umumiy ─────────────────────────────────────────────────────────────────
choose_language = "🌐 Tilni tanlang:"
btn_uz = "🇺🇿 O'zbek"
btn_ru = "🇷🇺 Русский"

enter_password = "🔑 Kirish parolini kiriting:"
wrong_password = "❌ Parol noto'g'ri. Qayta urinib ko'ring. ({attempts}/3)"
account_blocked = "⛔ Siz bloklandingiz. Admin bilan bog'laning."
account_deactivated = "⛔ Hisobingiz faolsizlantirilgan. Admin bilan bog'laning."

text_expected = "✍️ Iltimos, matn ko'rinishida yozing."
location_expected = "📍 Iltimos, joylashuvni tugma orqali yuboring."
invalid_number = "🔢 Faqat raqam kiriting."
action_cancelled = "❌ Amal bekor qilindi."
nothing_to_cancel = "ℹ️ Bekor qiladigan amal yo'q."

# ─── Sahifalash ─────────────────────────────────────────────────────────────
btn_back_to_list = "◀️ Ro'yxatga"
employees_list_header = "👥 <b>Hodimlar</b> — jami {total} ta"
reports_list_header = "📊 <b>Hisobotlar</b> — jami {total} ta"
pending_list_header = "✅ <b>Tasdiqlash kutilmoqda</b> — jami {total} ta"

# ─── Ro'yxatdan o'tish ──────────────────────────────────────────────────────
enter_full_name = "👤 Ism va familyangizni kiriting:"
enter_position = "💼 Lavozimingizni kiriting:"
choose_districts = "🗺 O'zingizga biriktirilgan tumanlarni tanlang:\n(Bir nechta tanlash mumkin)"
no_districts_selected = "⚠️ Kamida bitta tumanni tanlang."
choose_your_record = (
    "👤 Ro'yxatda o'zingizni toping:\n"
    "(Admin sizni oldindan kiritgan bo'lishi mumkin)"
)
btn_not_in_list = "➕ Ro'yxatda yo'qman"
record_already_taken = "⚠️ Bu yozuv allaqachon band. Boshqasini tanlang."
registration_complete = (
    "✅ Ro'yxatdan o'tdingiz!\n\n"
    "👤 Ism: {full_name}\n"
    "💼 Lavozim: {position}\n"
    "🗺 Tumanlar: {districts}"
)
new_employee_notify = (
    "🆕 Yangi hodim ro'yxatdan o'tdi:\n\n"
    "👤 {full_name}\n"
    "💼 {position}\n"
    "🗺 Tumanlar: {districts}"
)

# ─── Bosh menyu ─────────────────────────────────────────────────────────────
main_menu = "📌 Bosh menyu"
btn_report = "📋 Ma'lumot berish"
btn_settings = "⚙️ Sozlamalar"

# ─── Sozlamalar ─────────────────────────────────────────────────────────────
settings_menu = "⚙️ Sozlamalar"
btn_edit_districts = "📍 Tumanlarni tahrirlash"
btn_change_language = "🌐 Tilni o'zgartirish"
districts_updated = "✅ Tumanlar yangilandi."
language_changed = "✅ Til o'zgartirildi."

# ─── Hisobot ─────────────────────────────────────────────────────────────────
choose_report_type = "📋 Ma'lumot turi:"
btn_laboratory = "🔬 Laboratoriya"
btn_technical = "🔍 Texnik ko'rik"
btn_visual = "👁 Visual ko'rik"
btn_instrumental = "🔧 Instrumental ko'rik"

choose_partners = "🤝 Sheriklar (ixtiyoriy):\n(Birdan ortiq tanlash mumkin)"
btn_no_partner = "👤 Sherik yo'q"
btn_continue = "▶️ Davom etish"

choose_district = "🗺 Hudud tanlang:"
btn_other_district = "🔍 Boshqa hudud"
enter_customer = "🏢 Buyurtmachi nomini kiriting:"
send_location = "📍 Joylashuvingizni yuboring:"
btn_send_location = "📍 Joylashuvni yuborish"
send_photos = "📸 Rasmlarni yuboring ({min}-{max} ta):"
photos_progress = "📸 Yuborilgan rasmlar: {count} (kamida {min} ta kerak)"
btn_done = "✅ Tayyor"
min_photos_required = "📸 Kamida {min} ta rasm yuborish kerak."
max_photos_reached = "📸 Ko'pi bilan {max} ta rasm yuborish mumkin."
enter_plots_count = "🔢 Uchastkalar sonini kiriting yoki o'tkazib yuboring:"
btn_skip = "⏭ O'tkazib yuborish"

report_preview = (
    "📋 <b>Hisobotingizni tekshiring:</b>\n\n"
    "🏗 Turi: {report_type}\n"
    "📍 Hudud: {district}\n"
    "🏢 Buyurtmachi: {customer}\n"
    "🤝 Sheriklar: {partners}\n"
    "📸 Rasmlar: {photos_count} ta\n"
    "🗓 Sana: {date}\n"
    "🗺 Joylashuv: {location}"
)
report_preview_plots = "\n🔢 Uchastkalar: {plots_count}"
btn_submit = "✅ Yuborish"
btn_refill = "✏️ Qayta to'ldirish"

report_submitted = "✅ Hisobotingiz qabul qilindi!\nAdmin tasdiqlashini kuting."
report_cancelled = "❌ Hisobot bekor qilindi."
report_approved_notify = "✅ Hisobotingiz tasdiqlandi va kanalga yuborildi."
report_rejected_notify = (
    "❌ Hisobotingiz rad etildi. Batafsil ma'lumot uchun admin bilan bog'laning."
)

partner_notified = (
    "📋 <b>{sender}</b> sizni bugungi hisobotga sherik sifatida qo'shdi.\n\n"
    "👤 Hodim: {sender}\n"
    "💼 Lavozim: {position}\n"
    "🏗 Turi: {report_type}\n"
    "📍 Hudud: {district}\n"
    "🏢 Buyurtmachi: {customer}\n"
    "🤝 Sheriklar: {partners}\n"
    "🗓 Sana: {date}"
)

# ─── Report turlari (matn) ───────────────────────────────────────────────────
type_laboratory = "Laboratoriya"
type_visual = "Visual ko'rik"
type_instrumental = "Instrumental ko'rik"

# ─── Admin / SuperAdmin kirish ───────────────────────────────────────────────
admin_login_choice = "👋 Xush kelibsiz!\n\nQanday kirasiz?"
btn_login_as_employee = "👤 Hodim sifatida"
btn_login_as_admin = "🔐 Admin sifatida"

# ─── Admin menyu ────────────────────────────────────────────────────────────
admin_menu = "🔐 Admin panel"
btn_employees = "👥 Hodimlar"
btn_reports = "📊 Hisobotlar"
btn_attendance = "✅ Davomat tasdiqlash"
btn_change_password = "🔑 Parolni o'zgartirish"
btn_manage_roles = "👑 Rolni o'zgartirish"
btn_back = "◀️ Orqaga"

# ─── Hodimlar bo'limi ────────────────────────────────────────────────────────
employees_menu = "👥 Hodimlar bo'limi"
btn_list_employees = "📋 Ro'yxatni ko'rish"
btn_add_employee = "➕ Hodim qo'shish"
no_employees = "👥 Hozircha hodimlar yo'q."

employee_card = (
    "👤 <b>{full_name}</b>\n"
    "💼 {position}\n"
    "🔑 Rol: {role}\n"
    "🗺 Tumanlar: {districts}\n"
    "📅 Qo'shilgan: {created_at}\n"
    "📌 Holat: {status}"
)
status_active = "faol"
status_inactive = "faolsizlantirilgan"

btn_edit = "✏️ Tahrirlash"
btn_deactivate = "🚫 Faolsizlantirish"
btn_activate = "♻️ Tiklash"
btn_yes_deactivate = "✅ Ha, faolsizlantir"
confirm_deactivate = (
    "⚠️ Hodimni faolsizlantirmoqchimisiz?\n\n"
    "👤 {full_name}\n\n"
    "Hisobotlari saqlanib qoladi, lekin u botdan foydalana olmaydi."
)
employee_deactivated = "✅ Hodim faolsizlantirildi."
employee_activated = "✅ Hodim tiklandi."
cannot_deactivate_self = "⚠️ O'zingizni faolsizlantira olmaysiz."
btn_cancel = "❌ Bekor qilish"
employee_not_found = "❌ Hodim topilmadi."

add_employee_name = "👤 Yangi hodim ismini kiriting:"
add_employee_position = "💼 Lavozimini kiriting:"
add_employee_districts = "🗺 Tumanlarini tanlang:"
employee_added = (
    "✅ Hodim qo'shildi:\n👤 {full_name}\n💼 {position}\n\n"
    "U botga /start bosib kirganda o'z yozuvini tanlaydi."
)

edit_employee_menu = "✏️ Nima o'zgartirasiz?"
btn_edit_name = "👤 Ism"
btn_edit_position = "💼 Lavozim"
enter_new_name = "👤 Yangi ismni kiriting:"
enter_new_position = "💼 Yangi lavozimni kiriting:"
employee_updated = "✅ Ma'lumotlar yangilandi."

confirm_action = "✅ Tasdiqlash"
btn_confirm = "✅ Tasdiqlash"

# ─── Hisobotlar bo'limi ──────────────────────────────────────────────────────
reports_menu = "📊 Hisobotlar"
btn_today_reports = "📅 Bugungi hisobotlar"
btn_search_reports = "🔍 Qidirish"
no_reports = "📭 Hisobotlar topilmadi."
no_photos = "📭 Rasmlar topilmadi."

search_date = "📅 Sanani kiriting (masalan: 05.06.2026):"
search_employee = "👤 Hodimni tanlang:"
invalid_date = "❌ Noto'g'ri sana formati. Masalan: 05.06.2026"

report_card = (
    "👤 <b>{full_name}</b>\n"
    "💼 {position}\n"
    "🏗 {report_type}\n"
    "📍 {district}\n"
    "🏢 {customer}\n"
    "🤝 Sheriklar: {partners}\n"
    "🗓 {date}\n"
    "🗺 Joylashuv: {location}"
)
btn_view_photos = "📸 Rasmlarni ko'rish"

# ─── Davomat tasdiqlash ──────────────────────────────────────────────────────
attendance_menu = "✅ Tasdiqlash kutilmoqda"
no_pending = "✅ Tasdiqlanmagan hisobotlar yo'q."
btn_approve = "✅ Tasdiqlash"
btn_reject = "❌ Rad etish"
report_approved = "✅ Hisobot tasdiqlandi va kanalga yuborildi."
report_rejected = "❌ Hisobot rad etildi."
report_not_found = "❌ Hisobot topilmadi."
report_already_processed = "ℹ️ Bu hisobot allaqachon ko'rib chiqilgan."
report_not_approved = "❌ Hisobot tasdiqlanmadi."
channel_send_failed = "❌ Kanalga yuborishda xato:\n<code>{error}</code>"

channel_report = (
    "✅ <b>Davomat tasdiqlandi</b>\n\n"
    "👤 Hodim: {full_name}\n"
    "💼 Lavozim: {position}\n"
    "🏗 Turi: {report_type}\n"
    "📍 Hudud: {district}\n"
    "🏢 Buyurtmachi: {customer}\n"
    "🤝 Sheriklar: {partners}\n"
    "🗓 Sana: {date}\n"
    "🗺 Joylashuv: {location}"
)

# ─── Parol o'zgartirish ──────────────────────────────────────────────────────
enter_current_password = "🔑 Joriy parolni kiriting:"
enter_new_password = "🔑 Yangi parolni kiriting (kamida {min} ta belgi):"
enter_confirm_password = "🔑 Yangi parolni qayta kiriting:"
passwords_mismatch = "❌ Parollar mos kelmadi."
password_too_short = "❌ Parol kamida {min} ta belgidan iborat bo'lishi kerak."
password_changed = "✅ Parol muvaffaqiyatli o'zgartirildi."
wrong_current_password = "❌ Joriy parol noto'g'ri."

# ─── Rol boshqaruvi ──────────────────────────────────────────────────────────
roles_menu = "👑 Rolni o'zgartirish"
choose_employee_for_role = "👤 Hodimni tanlang:"
choose_new_role = "🔑 Yangi rolni tanlang:\n\n👤 {full_name} - hozirgi rol: {current_role}"
btn_make_admin = "👑 Admin qilish"
btn_make_employee = "👤 Hodimga qaytarish"
role_updated = "✅ {full_name} roli o'zgartirildi: {new_role}"
role_update_confirm = "👤 {full_name}\n📌 Yangi rol: {new_role}\n\nTasdiqlaysizmi?"

admin_assigned_notify = "🎉 Siz admin sifatida tayinlandingiz!"
admin_removed_notify = "📌 Sizning admin huquqlaringiz bekor qilindi."

# ─── Xatoliklar ─────────────────────────────────────────────────────────────
error_generic = "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring."
not_authorized = "⛔ Sizda bu amalni bajarish huquqi yo'q."
