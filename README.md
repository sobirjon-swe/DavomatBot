# DavomatBot

Toshkent viloyati bo'yicha ish davomatini yig'adigan Telegram bot.
Hodim joyidan hisobot yuboradi (tur, sherik, hudud, buyurtmachi, joylashuv,
3–7 rasm), admin uni tasdiqlaydi va hisobot kanalga chiqadi.

Texnologiyalar: Python 3.10+, aiogram 3, SQLAlchemy 2 (async), PostgreSQL, Alembic.

---

## Tuzilishi

```
bot/
  main.py            bot kirish nuqtasi: dispatcher, middleware, routerlar
  api_server.py      API kirish nuqtasi (uvicorn)
  config.py          .env dan sozlamalar + tekshiruv, tumanlar ro'yxati
  database/          models.py (sxema), crud.py (so'rovlar), session.py (engine)
  api/               Mini App uchun HTTP qatlami
    security.py        initData HMAC tekshiruvi — ishonch nuqtasi
    deps.py            sessiya, joriy foydalanuvchi, rol talablari
    schemas.py         so'rov/javob modellari
    routes_*.py        endpointlar
  handlers/          start.py, employee/, admin/
  keyboards/         inline va reply klaviaturalar, sahifalash
  filters/           rolga asoslangan ruxsat filtrlari
  middlewares/       auth.py — har bir yangilanishga db_user biriktiradi
  locales/           uz.py, ru.py va t() funksiyasi
  utils/             formatters, notifications, channel, messages
  alembic/           migratsiyalar
  tests/             pytest
```

Bot va API alohida jarayonlar: biri qulasa ikkinchisi ishlab turaveradi.
Umumiy qismi — `config`, `database` va `utils`.

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

## Mini App API

Telegram Mini App uchun HTTP qatlami. Bot bilan bir xil `config`, `database`
va `utils` modullarini ishlatadi, lekin **alohida jarayonda** ishlaydi.

```bash
cd bot
python api_server.py          # yoki: uvicorn api.app:app --port 8000
```

Interaktiv hujjat: `http://127.0.0.1:8000/api/docs`

### Autentifikatsiya

Mini App brauzerda ishlaydi, ya'ni u yuborgan hamma narsani foydalanuvchi
o'zgartira oladi. Yagona ishonchli narsa — Telegram bot tokeni bilan qo'ygan
HMAC imzosi. Har bir so'rovda `initData` yuboriladi va qayta tekshiriladi:

```
Authorization: tma <initData>
```

Alohida sessiya tokeni (JWT) **ataylab berilmaydi**: HMAC hisobi
mikrosoniyalar oladi, lekin o'g'irlanishi mumkin bo'lgan uzoq muddatli token
umuman paydo bo'lmaydi. Tekshiruv `api/security.py` da, unga 17 ta test
yozilgan (`tests/test_api_security.py`) — jumladan imzodan keyin `user.id`
almashtirilgan, boshqa token bilan imzolangan va muddati o'tgan holatlar.

### Endpointlar

| Metod | Yo'l | Kim |
|---|---|---|
| GET | `/api/me` | hamma |
| PATCH | `/api/me/language` | hamma |
| PUT | `/api/me/districts` | hamma |
| GET | `/api/districts` | hamma |
| GET | `/api/reports?day=&user_id=&status=&page=` | hodim faqat o'zinikini |
| GET | `/api/reports/{id}` | qatnashganlar va admin |
| POST | `/api/reports` | hodim |
| POST | `/api/reports/{id}/approve` | admin |
| POST | `/api/reports/{id}/reject` | admin |
| POST | `/api/photos` | hamma |
| GET | `/api/employees?page=&per_page=` | admin |
| POST | `/api/employees` | admin |
| PATCH | `/api/employees/{id}` | admin |
| POST | `/api/employees/{id}/deactivate` \| `/activate` | superadmin |
| PATCH | `/api/employees/{id}/role` | superadmin |

Xatolar bir xil ko'rinishda qaytadi, frontend `code` bo'yicha ish tutadi:

```json
{"detail": {"code": "not_registered", "message": "Avval botda ro'yxatdan o'ting"}}
```

### Rasmlar

Mini App Telegram `file_id` ishlab chiqara olmaydi — u faqat bayt yuboradi.
Shuning uchun `POST /api/photos` rasmni yopiq **ombor chatiga**
(`STORAGE_CHAT_ID`) yuboradi, Telegram `file_id` qaytaradi va bazaga o'sha
yoziladi. Natijada kanalga chiqarish mantig'i umuman o'zgarmaydi.

Yopiq kanal yarating, botni admin qilib qo'shing va uning ID sini
`STORAGE_CHAT_ID` ga yozing.

### Prodda

```nginx
server {
    server_name davomat.example.uz;
    location /api/ { proxy_pass http://127.0.0.1:8000; }
    location / { root /var/www/davomat; try_files $uri /index.html; }
}
```

HTTPS majburiy (Telegram Mini App HTTP manzilni ochmaydi) — `certbot --nginx`.
Keyin @BotFather da `/newapp` orqali `WEBAPP_URL` ni ko'rsating.

## Mini App (frontend)

`webapp/` — React 19 + TypeScript + Vite + Tailwind + shadcn/ui +
`@telegram-apps/sdk-react`.

```bash
cd webapp
corepack enable            # pnpm ni yoqadi
pnpm install
pnpm dev                   # http://localhost:5173
pnpm build                 # dist/ ga yig'adi (ichida tsc -b ham bor)
```

### Mavzu

Ranglar Telegramdan keladi: SDK `--tg-theme-*` CSS o'zgaruvchilarini
hujjatga qo'yadi, `src/index.css` ularni ilova tokenlariga ulaydi,
`tailwind.config.js` esa shadcn nomlariga (`bg-background`, `text-primary`
va h.k.) bog'laydi. Natijada ilova foydalanuvchining kunduzgi/tungi
rejimiga hech qanday qo'shimcha kodsiz moslashadi.

Shu sababli shadcn ning odatdagi `hsl(var(--token))` sxemasi o'rniga
tokenlar to'g'ridan-to'g'ri rang qiymati sifatida ishlatilgan — Telegram
ranglarni HEX ko'rinishida beradi.

### Autentifikatsiya

`useRawInitData()` bergan satr har bir so'rovda `Authorization: tma ...`
sarlavhasida yuboriladi. Brauzerda (Telegramdan tashqarida) initData
bo'lmaydi — lokal sinov uchun `.env.local` ga `VITE_DEV_INIT_DATA` yozing.

### Botdan ochish

`WEBAPP_URL` to'ldirilgandan keyin bot ilovaga ikki yo'l beradi:

1. **Doimiy menyu tugmasi** — kiritish maydoni yonida, barcha foydalanuvchilar
   uchun. Bot ishga tushganda avtomatik o'rnatiladi.
2. **Asosiy menyudagi "📱 Ilovani ochish"** tugmasi — hodim va admin
   klaviaturalarida.

`WEBAPP_URL` bo'sh bo'lsa tugmalar umuman ko'rsatilmaydi va menyu tugmasi
oddiy buyruqlar ro'yxatiga qaytariladi — ishlamaydigan tugma qolib
ketmasligi uchun. Manzil `https://` bilan boshlanmasa bot ishga tushishda
tushunarli xato bilan to'xtaydi.

### Nima tayyor

| Ekran | Holat |
|---|---|
| Hisobotlar ro'yxati (filtr: kutilmoqda / tasdiqlangan / hammasi) | tayyor |
| Hisobot kartochkasi, xaritada ochish, tasdiqlash/rad etish | tayyor |
| Hodimlar ro'yxati (admin) | tayyor |
| Hisobot yuborish formasi | keyingi bosqich |

Hodim faqat o'zi qatnashgan hisobotlarni ko'radi — bu serverda
majburlanadi, frontend faqat shunga mos ko'rinish beradi.

## Testlar va linter

```bash
cd bot
pip install -r requirements-dev.txt
pytest          # 120 ta test, ~13 soniya
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
| `Mini App` | Frontend tiplari va build |
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

Birinchi marta o'rnatish — **[deploy/README.md](deploy/README.md)**: systemd
xizmatlari, nginx, sertifikat, ombor kanali va Alembic ni mavjud bazaga ulash.

Keyin `main` branchiga push qilinganda hammasi avtomatik ketadi
(`.github/workflows/deploy.yml`):

1. Mini App GitHub Actions da yig'iladi (VPS ga Node kerak emas)
2. `dist/` → `/var/www/davomat` ga yuklanadi
3. Backend yangilanadi, `alembic upgrade head` bajariladi
4. `davomat` va `davomat-api` xizmatlari qayta ishga tushadi
5. Ikkalasi ishlayotgani va `/api/health` javob berayotgani tekshiriladi

Har qadam xatosida deploy to'xtaydi.

| Fayl | Nima |
|---|---|
| `deploy/davomat.service` | Bot xizmati |
| `deploy/davomat-api.service` | Mini App API xizmati |
| `deploy/nginx-davomat.conf` | nginx: statik fayllar + `/api/` proksi |

GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
