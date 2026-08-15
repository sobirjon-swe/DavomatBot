# DavomatBot

Toshkent viloyati bo'yicha ish davomatini yig'adigan Telegram bot.
Hodim joyidan hisobot yuboradi (tur, sherik, hudud, buyurtmachi, joylashuv,
3–7 rasm), admin uni tasdiqlaydi va hisobot kanalga chiqadi.

Texnologiyalar: Python 3.10+, aiogram 3, SQLAlchemy 2 (async), PostgreSQL, Alembic.

---

## Tuzilishi

```
bot/
  main.py            kirish nuqtasi: dispatcher, middleware, routerlar
  config.py          .env dan sozlamalar + tekshiruv, tumanlar ro'yxati
  database/          models.py (sxema), crud.py (so'rovlar), session.py (engine)
  handlers/          start.py, employee/, admin/
  keyboards/         inline va reply klaviaturalar
  filters/           rolga asoslangan ruxsat filtrlari
  middlewares/       auth.py — har bir yangilanishga db_user biriktiradi
  locales/           uz.py, ru.py va t() funksiyasi
  utils/             formatters, notifications, channel, messages
  alembic/           migratsiyalar
```

## Ishga tushirish

```bash
cd bot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # va qiymatlarni to'ldiring
alembic upgrade head
python main.py
```

### .env

| O'zgaruvchi | Majburiy | Izoh |
|---|---|---|
| `BOT_TOKEN` | ha | @BotFather bergan token |
| `DATABASE_URL` | ha | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SUPERADMIN_ID` | ha | SuperAdmin Telegram ID raqami |
| `CHANNEL_ID` | ha | Kanal ID si — **taklif havolasi emas**, `-100...` raqam |
| `REDIS_URL` | yo'q | Berilsa FSM holati Redisda saqlanadi |
| `INITIAL_ACCESS_PASSWORD` | yo'q | Birinchi ishga tushishdagi parol |
| `LOG_LEVEL` | yo'q | `INFO` (standart) |

`BOT_TOKEN` yoki `CHANNEL_ID` noto'g'ri bo'lsa bot ishga tushishda tushunarli
xato bilan to'xtaydi.

## Kirish paroli

Bazada faol parol bo'lmasa, bot birinchi ishga tushishda `INITIAL_ACCESS_PASSWORD`
ni o'rnatadi; u berilmagan bo'lsa tasodifiy parol yaratib **logga bir marta**
yozadi. Parolni admin panelidan (`🔑 Parolni o'zgartirish`) yoki skript orqali
almashtirish mumkin:

```bash
python reset_password.py "yangi-parol"
```

## Migratsiyalar

Sxema faqat Alembic orqali o'zgaradi — `create_all` ishlatilmaydi.

**Yangi (bo'sh) baza:**

```bash
alembic upgrade head
```

**Allaqachon ishlab turgan baza** (jadvallar `create_all` bilan yaratilgan) —
`0001` o'sha mavjud holatni tasvirlaydi, shuning uchun uni qayta bajarmasdan
belgilab qo'yish kerak, aks holda "jadval allaqachon mavjud" xatosi chiqadi:

```bash
alembic stamp 0001      # BIR MARTA, faqat eski bazada
alembic upgrade head    # 0002 ni qo'llaydi
```

Yangi migratsiya yaratish:

```bash
alembic revision --autogenerate -m "nima o'zgardi"
```

## Testlar va linter

```bash
cd bot
pip install -r requirements-dev.txt
pytest          # 69 ta test, ~10 soniya
ruff check .
```

Standart holatda testlar xotiradagi SQLite da ishlaydi — hech narsa
sozlash shart emas. Ammo SQLite vaqt mintaqasini saqlamaydi, shuning uchun
`TIMESTAMPTZ` ga bog'liq testlar o'tkazib yuboriladi. Ularni ishga tushirish
uchun haqiqiy PostgreSQL kerak:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/davomat_test pytest
```

CI (`.github/workflows/ci.yml`) har PR da uch ishni bajaradi:

| Ish | Nima tekshiriladi |
|---|---|
| `Ruff` | Kod uslubi, ishlatilmagan importlar |
| `Testlar` | Python 3.10 va 3.11 da, PostgreSQL service bilan |
| `Migratsiyalar` | `upgrade head` → `downgrade base` → `upgrade head`, hamda modellar bilan migratsiyalar mos kelishi |

Oxirgi tekshiruv muhim: modelga ustun qo'shib, migratsiya yozilmasa CI
qizil bo'ladi — ilgari bunday o'zgarish jimgina prodga chiqib ketardi.

## Rollar

| Rol | Imkoniyatlar |
|---|---|
| `employee` | Hisobot yuborish, o'z tumanlari va tilini sozlash |
| `admin` | + hodimlar ro'yxati/tahriri, hisobotlar, davomat tasdiqlash, parol |
| `superadmin` | + rol berish, hodimni faolsizlantirish/tiklash |

Ruxsat router darajasidagi filtrlar bilan tekshiriladi (`filters/roles.py`),
shuning uchun inline tugmalar ham himoyalangan.

## Hodim qo'shishning ikki yo'li

1. **O'zi ro'yxatdan o'tadi** — `/start` → til → kirish paroli → ism, lavozim, tumanlar.
2. **Admin oldindan kiritadi** — `👥 Hodimlar → ➕ Hodim qo'shish`. Bunday yozuvda
   `telegram_id` bo'sh turadi; hodim botga birinchi kirganda ro'yxatdan o'zini
   tanlaydi va yozuv uning hisobiga bog'lanadi.

## Ma'lumotlar haqida

* Barcha vaqtlar bazada **UTC** (`TIMESTAMPTZ`), foydalanuvchiga `Asia/Tashkent`
  bo'yicha ko'rsatiladi. "Bugungi hisobotlar" ham Toshkent kuni bo'yicha.
* Hodim o'chirilmaydi, faolsizlantiriladi — hisobotlar tarixi saqlanib qoladi.
* Rad etilgan hisobot ham o'chirilmaydi, `is_rejected` bilan belgilanadi.

## Deploy

`main` branchiga push qilinganda `.github/workflows/deploy.yml` VPS'ga ulanib
kodni yangilaydi, bog'liqliklarni o'rnatadi, `alembic upgrade head` bajaradi va
`davomat` xizmatini qayta ishga tushiradi. Har qadam xatosida deploy to'xtaydi,
oxirida xizmat haqiqatan ishlayotgani tekshiriladi.

GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
