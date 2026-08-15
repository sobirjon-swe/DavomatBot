# Serverga o'rnatish

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

Deploy workflow `systemctl restart` ni `sudo` siz chaqiradi. Deploy
foydalanuvchisi `root` bo'lmasa, unga ruxsat bering:

```bash
# /etc/sudoers.d/davomat-deploy
deployuser ALL=(root) NOPASSWD: /bin/systemctl restart davomat davomat-api
```

va workflow dagi `systemctl restart` ni `sudo systemctl restart` ga o'zgartiring.

## 5. nginx va sertifikat

```bash
sudo mkdir -p /var/www/davomat
sudo chown -R $USER:$USER /var/www/davomat

sudo cp deploy/nginx-davomat.conf /etc/nginx/sites-available/davomat
sudo nano /etc/nginx/sites-available/davomat        # domenni yozing
sudo ln -s /etc/nginx/sites-available/davomat /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d davomat.example.uz
```

Sozlamada ikki nozik joy bor, ikkalasi ham faylda izohlangan:

- **`X-Frame-Options` qo'yilmagan.** Telegram Web da Mini App iframe ichida
  ochiladi va bu sarlavha uni butunlay bloklaydi. Mobil ilovada WebView
  bo'lgani uchun muammo sezilmaydi — xato faqat brauzerdagi Telegramda chiqadi.
- **`client_max_body_size 12m`.** nginx dagi standart chegara 1 MB va u
  10 MB lik rasmni 413 bilan qaytarib yuborardi.

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
