# Serverga o'rnatish

> **Yangi, bo'sh server bo'lsa** — avval quyidagi "Noldan ko'tarish"
> bo'limini bajaring. Undan keyingi bo'limlar allaqachon ishlab turgan
> serverni yangilash uchun.

---

## Noldan ko'tarish

Deploy skripti repo `/home/DavomatBot/bot` da turadi va `.venv` mavjud deb
hisoblaydi. Yangi serverda ularni bir marta qo'lda yaratish kerak.

```bash
# 1. Tizim paketlari
sudo apt update
sudo apt install -y python3.11 python3.11-venv git postgresql nginx certbot python3-certbot-nginx

# 2. Baza
sudo -u postgres psql -c "CREATE USER davomat WITH PASSWORD 'kuchli-parol';"
sudo -u postgres psql -c "CREATE DATABASE davomat_db OWNER davomat;"

# 3. Repo
sudo mkdir -p /home/DavomatBot
sudo chown $USER:$USER /home/DavomatBot
git clone https://github.com/sobirjon-swe/DavomatBot.git /home/DavomatBot
cd /home/DavomatBot/bot

# 4. Virtual muhit
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Sozlamalar
cp .env.example .env
nano .env        # BOT_TOKEN, DATABASE_URL, SUPERADMIN_ID, CHANNEL_ID
chmod 600 .env
```

### Alembic — bu yerda ehtiyot bo'ling

Ikki holat bor va ular bir-biriga o'xshamaydi:

| Holat | Buyruq |
|---|---|
| **Yangi, bo'sh baza** | `alembic upgrade head` |
| Eski serverdan `pg_dump` bilan ko'chirilgan ma'lumot | `alembic stamp 0001` → `alembic upgrade head` |

Bo'sh bazada `stamp 0001` **qilmang**: u jadvallarni yaratmasdan
"yaratilgan" deb belgilab qo'yadi va bot bo'sh bazaga urilib xato beradi.

Ma'lumotni ko'chirish:

```bash
# eski serverda
pg_dump -Fc davomat_db > davomat.dump
# yangi serverda
pg_restore -d davomat_db davomat.dump
alembic stamp 0001 && alembic upgrade head
```

### Tekshirish

```bash
python main.py        # Ctrl+C bilan to'xtating
```

Bot ishga tushsa, quyidagi bo'limlarga o'ting: foydalanuvchi, systemd,
nginx, sertifikat.

### GitHub secrets

Actions → Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
`VPS_USER` ning ochiq kaliti serverdagi `~/.ssh/authorized_keys` da
bo'lishi shart, aks holda deploy SSH bosqichida to'xtaydi.

Tekshirish: o'z mashinangizdan `ssh -i <kalit> VPS_USER@VPS_HOST "echo ok"`.

---


Ubuntu 22.04 uchun. Domen o'rniga `davomat.example.uz` yozilgan — o'zingiznikiga
almashtiring.

Tartib muhim: **avval xizmatlar yaratiladi, keyingina `main` ga merge qilinadi.**
Deploy workflow `davomat-api` ni qayta ishga tushirishga urinadi va u hali
mavjud bo'lmasa deploy yiqiladi.

---

## 0. Merge qilishdan oldin

- [ ] **Tokenni @BotFather da revoke qiling.** Eski token git tarixida qolgan.
      Yangisini VPS dagi `.env` ga yozing.
- [ ] `.env` dagi `CHANNEL_ID` raqam ekanini tekshiring (`-100...`), taklif
      havolasi emas — aks holda bot ishga tushishda to'xtaydi.
- [ ] Baza nusxasini oling: `pg_dump -Fc davomat_db > ~/davomat-$(date +%F).dump`

## 1. Alembic ni mavjud bazaga ulash

Jadvallar ilgari `create_all` bilan yaratilgan, `0001` migratsiyasi esa aynan
o'sha holatni tasvirlaydi. Shuning uchun uni **bajarmasdan** belgilab qo'yish
kerak, aks holda "jadval allaqachon mavjud" xatosi chiqadi:

```bash
cd /home/DavomatBot/bot
source .venv/bin/activate
alembic stamp 0001        # BIR MARTA, faqat eski bazada
alembic upgrade head      # 0002 ni qo'llaydi
```

## 2. Xizmat uchun foydalanuvchi

Bot va API `root` sifatida ishlamasligi kerak:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin davomat
sudo chown -R davomat:davomat /home/DavomatBot
sudo chmod 600 /home/DavomatBot/bot/.env
```

## 3. Rasmlar uchun ombor kanali

Mini App Telegram `file_id` ishlab chiqara olmaydi, shuning uchun rasm avval
yopiq kanalga yuboriladi.

1. Yopiq kanal yarating (masalan "Davomat — media").
2. Botni unga **admin** qilib qo'shing.
3. Kanal ID sini oling va `.env` ga yozing:

```
STORAGE_CHAT_ID=-1009876543210
```

## 4. systemd xizmatlari

```bash
sudo cp deploy/davomat.service deploy/davomat-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now davomat davomat-api

systemctl status davomat davomat-api
journalctl -u davomat-api -n 50
```

Unit fayllarida systemd ning himoya sozlamalari yoqilgan (`ProtectSystem`,
`NoNewPrivileges`, `MemoryDenyWriteExecute` va h.k.). Agar xizmat tushunarsiz
xato bilan ishga tushmasa, birinchi bo'lib `MemoryDenyWriteExecute=true` ni
o'chirib ko'ring — u ba'zi C/Rust kengaytmalari bilan ziddiyatga kirishi
mumkin. Sababni `journalctl -u davomat -n 50` ko'rsatadi.

### Deploy uchun tor sudoers qoidasi

Deploy workflow'i root bo'lmagan foydalanuvchi ostida ham ishlaydi — u
`sudo` ni faqat kerak bo'lganda chaqiradi. To'liq huquq bermang, faqat
kerakli buyruqlarga ruxsat bering:

```bash
# /etc/sudoers.d/90-davomat-deploy   (chmod 440)
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart davomat, \
                            /usr/bin/systemctl restart davomat-api, \
                            /usr/bin/mkdir -p /var/www/davomat, \
                            /usr/bin/chown * /var/www/davomat
```

`deploy` o'rniga `VPS_USER` dagi nomni yozing. `systemctl` yo'lini
tekshiring: `command -v systemctl` (odatda `/usr/bin/systemctl`, ba'zi
tizimlarda `/bin/systemctl`).

Sir sizib chiqqan taqdirda hujumchi xizmatni qayta ishga tushirishi,
shuningdek `/var/www/davomat` (nginx statik web root, 5-bo'limga qarang)
egaligini o'ziga o'tkazib, u yerdagi fayllarni almashtirishi mumkin — bu
ro'yxatni faqat haqiqatan kerak bo'lgan buyruqlar bilan cheklab turing.

**Bootstrap** boshqa masala: u paket o'rnatadi, foydalanuvchi yaratadi va
systemd unit qo'yadi, ya'ni to'liq huquq talab qiladi. Uni bir marta root
sifatida bajarish eng sodda yo'l.

## 5. nginx va sertifikat

`nginx-davomat.conf` 443-blokda sertifikat yo'liga to'g'ridan-to'g'ri
ishora qiladi, shuning uchun uni **sertifikat olingandan keyin**
o'rnatish kerak — aks holda `nginx -t` hali mavjud bo'lmagan faylga
ishora qilgani uchun yiqiladi. To'g'ri ketma-ketlik ikki bosqich:

```bash
sudo mkdir -p /var/www/davomat
sudo chown -R $USER:$USER /var/www/davomat

# 1-bosqich: faqat 80-portli vaqtinchalik fayl bilan sertifikat olish
cat <<'EOF' | sudo tee /etc/nginx/sites-available/davomat
server {
    listen 80;
    listen [::]:80;
    server_name davomat.example.uz;
    location / { return 200 'ok'; }
}
EOF
sudo ln -sf /etc/nginx/sites-available/davomat /etc/nginx/sites-enabled/davomat
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --nginx -d davomat.example.uz

# 2-bosqich: sertifikat tayyor — endi to'liq konfiguratsiyani o'rnatish
sudo cp deploy/nginx-davomat.conf /etc/nginx/sites-available/davomat
sudo sed -i 's/davomat.example.uz/SIZNING-DOMENINGIZ/g' \
    /etc/nginx/sites-available/davomat
sudo nginx -t && sudo systemctl reload nginx
```

Sozlamada uchta nozik joy bor, hammasi faylda izohlangan:

- **`X-Frame-Options` qo'yilmagan.** Telegram Web da Mini App iframe ichida
  ochiladi va bu sarlavha uni butunlay bloklaydi. Mobil ilovada WebView
  bo'lgani uchun muammo sezilmaydi — xato faqat brauzerdagi Telegramda chiqadi.
- **`client_max_body_size 12m`.** nginx dagi standart chegara 1 MB va u
  10 MB lik rasmni 413 bilan qaytarib yuborardi.
- **`listen 443 ssl http2;`** (eski sintaksis). nginx 1.25.1 dan oldingi
  versiyalarda (masalan Ubuntu 24.04 dagi 1.24.0) alohida `http2 on;`
  direktivasi mavjud emas — `nginx -t` "unknown directive" bilan yiqiladi.

## 6. WEBAPP_URL va botni qayta ishga tushirish

```
WEBAPP_URL=https://davomat.example.uz
```

```bash
sudo systemctl restart davomat
```

Bot ishga tushganda menyu tugmasini o'zi o'rnatadi. @BotFather shart emas,
lekin `/newapp` orqali to'g'ridan-to'g'ri havola ham olishingiz mumkin.

Manzil `https://` bilan boshlanmasa bot ishga tushmaydi — Telegram
shifrlanmagan manzilni ochmaydi, shuning uchun xato startda ushlanadi.

## 7. Tekshirish

```bash
curl -fsS https://davomat.example.uz/api/health          # {"ok":true}
curl -sI https://davomat.example.uz | grep -i frame      # bo'sh bo'lishi kerak
journalctl -u davomat -u davomat-api -f
```

Telefonda: botga `/start` → "📱 Ilovani ochish".

---

## Keyin

Deploy `main` ga push bo'lganda avtomatik ishlaydi:
frontend GitHub Actions da yig'iladi → `/var/www/davomat` ga yuklanadi →
backend yangilanadi → migratsiya → ikkala xizmat qayta ishga tushadi →
`/api/health` tekshiriladi.

Har qadam xatosida deploy to'xtaydi.

### Foydali buyruqlar

```bash
journalctl -u davomat -f                 # bot loglari
journalctl -u davomat-api -f             # API loglari
systemctl restart davomat davomat-api    # qayta ishga tushirish
alembic current                          # bazadagi migratsiya versiyasi
alembic downgrade -1                     # oxirgi migratsiyani qaytarish
```

### Zaxira nusxa

Davomat ma'lumoti yo'qolsa tiklab bo'lmaydi. Kunlik `pg_dump`:

```bash
# /etc/cron.daily/davomat-backup
#!/bin/sh
set -e
pg_dump -Fc davomat_db > /var/backups/davomat-$(date +%F).dump
find /var/backups -name 'davomat-*.dump' -mtime +30 -delete
```
