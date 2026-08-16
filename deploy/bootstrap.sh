#!/usr/bin/env bash
#
# Serverni noldan tayyorlaydi. Qayta-qayta ishlatish xavfsiz: mavjud
# narsalarga tegmaydi, faqat yetishmayotganini qo'shadi.
#
# Ishlatish (GitHub Actions "Bootstrap server" workflow i shuni chaqiradi):
#   BOT_TOKEN=... SUPERADMIN_ID=... CHANNEL_ID=... DB_PASSWORD=... bash bootstrap.sh
#
# Talab: root yoki parolsiz sudo huquqi.

set -euo pipefail

APP_DIR="${APP_DIR:-/home/DavomatBot}"
BOT_DIR="$APP_DIR/bot"
REPO="${REPO:-https://github.com/sobirjon-swe/DavomatBot.git}"
BRANCH="${BRANCH:-main}"
# Python versiyasi qat'iy belgilanmaydi: Ubuntu 22.04 da 3.10, 24.04 da
# 3.12 keladi va aniq versiyani talab qilish deadsnakes PPA ni majburlardi.
# Loyiha 3.10+ da ishlaydi, shuning uchun mavjudini topamiz.
PYTHON="${PYTHON:-}"

DB_NAME="${DB_NAME:-davomat_db}"
DB_USER="${DB_USER:-davomat}"
SERVICE_USER="${SERVICE_USER:-davomat}"

log() { printf '\n==> %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# ─── 1. Tizim paketlari ─────────────────────────────────────────────────────

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    have "$candidate" || continue
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null
    then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

log "Tizim paketlari"
NEED_PG=1
[ -n "${DATABASE_URL:-}" ] && NEED_PG=0

[ -n "$PYTHON" ] || PYTHON=$(find_python || true)

if [ -z "$PYTHON" ] || ! have git || { [ "$NEED_PG" = "1" ] && ! have psql; }; then
  $SUDO apt-get update -qq
  # Aniq versiya emas, umumiy paketlar: distributiv o'zinikini beradi
  PACKAGES="python3 python3-venv git"
  [ "$NEED_PG" = "1" ] && PACKAGES="$PACKAGES postgresql"
  # shellcheck disable=SC2086
  $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $PACKAGES
  [ -n "$PYTHON" ] || PYTHON=$(find_python || true)
fi

if [ -z "$PYTHON" ]; then
  echo "XATO: Python 3.10 yoki yangirog'i topilmadi."
  exit 1
fi
echo "Python: $PYTHON ($("$PYTHON" --version))"

# venv moduli alohida paketda bo'lishi mumkin (Debian/Ubuntu). Paket nomi
# aynan $PYTHON versiyasiga mos bo'lishi kerak — "python3-venv" generic
# paket faqat distributivning standart python3 (masalan 3.10) uchun venv
# qo'shadi, agar $PYTHON boshqa versiya (masalan deadsnakes'dan 3.11)
# bo'lsa, "$PYTHON -m venv" baribir "ensurepip is not available" bilan
# yiqiladi.
if ! "$PYTHON" -c "import venv" 2>/dev/null; then
  $SUDO apt-get update -qq
  $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${PYTHON}-venv" \
    || $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv
fi

# ─── 2. Baza ────────────────────────────────────────────────────────────────

if [ -n "${DATABASE_URL:-}" ]; then
  log "Baza: tayyor DATABASE_URL ishlatiladi"
  echo "Foydalanuvchi va baza yaratilmaydi — ular allaqachon mavjud deb hisoblanadi."
else
  log "PostgreSQL foydalanuvchisi va bazasi"
  : "${DB_PASSWORD:?DB_PASSWORD yoki DATABASE_URL berilishi kerak}"

  $SUDO systemctl enable --now postgresql

  user_exists=$($SUDO -u postgres psql -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" || true)
  if [ "$user_exists" = "1" ]; then
    echo "Foydalanuvchi '$DB_USER' bor — paroli yangilanadi."
    $SUDO -u postgres psql -q -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
  else
    $SUDO -u postgres psql -q -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
  fi

  db_exists=$($SUDO -u postgres psql -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" || true)
  if [ "$db_exists" = "1" ]; then
    echo "Baza '$DB_NAME' allaqachon bor — tegilmaydi."
  else
    $SUDO -u postgres psql -q -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
  fi
fi

# ─── 3. Repo ────────────────────────────────────────────────────────────────

# Tizim darajasida ishonchli deb belgilanadi — pastda $APP_DIR egaligi
# xizmat foydalanuvchisiga o'tkaziladi, shundan keyin bu katalogda Git
# root, VPS_USER yoki xizmat foydalanuvchisi nomidan ishlatilishi mumkin
# (masalan Deploy workflow i orqali) — aks holda "dubious ownership" bilan
# yiqiladi (CVE-2022-24765).
if ! git config --system --get-all safe.directory 2>/dev/null | grep -qxF "$APP_DIR"; then
  $SUDO git config --system --add safe.directory "$APP_DIR"
fi

log "Repo: $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
  git -C "$APP_DIR" checkout --quiet "$BRANCH"
  git -C "$APP_DIR" reset --hard --quiet "origin/$BRANCH"
else
  $SUDO mkdir -p "$APP_DIR"
  $SUDO chown "$(id -un):$(id -gn)" "$APP_DIR"
  git clone --quiet --branch "$BRANCH" "$REPO" "$APP_DIR"
fi

# ─── 4. Virtual muhit ───────────────────────────────────────────────────────

log "Virtual muhit va bog'liqliklar"
cd "$BOT_DIR"
[ -d .venv ] || "$PYTHON" -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

# ─── 5. Sozlamalar ──────────────────────────────────────────────────────────

log "Sozlamalar (.env)"
if [ -f .env ]; then
  echo ".env allaqachon bor — tegilmaydi."
else
  : "${BOT_TOKEN:?BOT_TOKEN berilmagan}"
  : "${SUPERADMIN_ID:?SUPERADMIN_ID berilmagan}"
  : "${CHANNEL_ID:?CHANNEL_ID berilmagan}"

  if [ -n "${DATABASE_URL:-}" ]; then
    DB_URL="$DATABASE_URL"
  else
    # Parol URL ichiga tushadi: `@`, `:`, `/`, `#` kabi belgilar ajratuvchi
    # sifatida o'qilib ulanishni buzardi, shuning uchun kodlanadi.
    # Qiymat argument emas, muhit orqali beriladi — `ps` da ko'rinmasin.
    DB_PASSWORD_ENC=$("$PYTHON" -c \
      'import os, urllib.parse; print(urllib.parse.quote(os.environ["DB_PASSWORD"], safe=""))')
    DB_URL="postgresql+asyncpg://$DB_USER:$DB_PASSWORD_ENC@127.0.0.1:5432/$DB_NAME"
  fi

  umask 077
  cat > .env <<ENVFILE
BOT_TOKEN=$BOT_TOKEN
DATABASE_URL=$DB_URL
SUPERADMIN_ID=$SUPERADMIN_ID
CHANNEL_ID=$CHANNEL_ID
LOG_LEVEL=INFO
ENVFILE
  echo ".env yaratildi."
fi
chmod 600 .env

# ─── 6. Migratsiyalar ───────────────────────────────────────────────────────

log "Migratsiyalar"
current=$(./.venv/bin/alembic current 2>/dev/null | tr -d '[:space:]' || true)

# Jadvallar sonini ilovaning o'z ulanishi orqali sanaymiz. `psql` orqali
# emas: baza boshqa serverda yoki boshqa nom ostida bo'lishi mumkin,
# .env dagi manzil esa doim to'g'ri.
tables=$(./.venv/bin/python - <<'PY' 2>/dev/null || echo 0
import asyncio
from sqlalchemy import text
from database.session import close_engine, engine

async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name <> 'alembic_version'"
        ))
        print(result.scalar())
    await close_engine()

asyncio.run(main())
PY
)

if [ -n "$current" ]; then
  echo "Alembic ulangan ($current) — yangilanadi."
  ./.venv/bin/alembic upgrade head
elif [ "$tables" -gt 0 ]; then
  # Eski, create_all bilan yaratilgan baza. Avtomatik stamp qilmaymiz:
  # bu ma'lumotli bazaga aralashish va qaror odamga tegishli.
  echo "XATO: bazada $tables ta jadval bor, lekin Alembic ulanmagan."
  echo "Agar bu eski bazadan ko'chirilgan ma'lumot bo'lsa, bir marta:"
  echo "  cd $BOT_DIR && ./.venv/bin/alembic stamp 0001 && ./.venv/bin/alembic upgrade head"
  exit 1
else
  echo "Bo'sh baza — sxema noldan yaratiladi."
  ./.venv/bin/alembic upgrade head
fi

# ─── 7. Mini App uchun katalog ──────────────────────────────────────────────

log "Statik fayllar katalogi"
WEB_ROOT="${WEB_ROOT:-/var/www/davomat}"
$SUDO mkdir -p "$WEB_ROOT"
# Egalik SSH foydalanuvchisiga beriladi: deploy workflow i frontendni shu
# yerga scp bilan yuklaydi va buni root siz qila olishi kerak.
$SUDO chown "$(id -un):$(id -gn)" "$WEB_ROOT"
echo "$WEB_ROOT tayyor."

# ─── 8. Xizmat ──────────────────────────────────────────────────────────────

log "systemd xizmati"
id -u "$SERVICE_USER" >/dev/null 2>&1 \
  || $SUDO useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"

# $APP_DIR ni $SERVICE_USER ga BUTUNLAY o'tkazib yubormaymiz — Deploy
# workflow i git pull/pip install ni VPS_USER nomidan (SSH orqali) doim
# takrorlab turadi, va u egalikni yo'qotsa "Permission denied" bilan
# yiqiladi. $SERVICE_USER (davomat) kodni FAQAT o'qiydi (davomat.service
# ProtectHome=read-only, PYTHONDONTWRITEBYTECODE=1) — shuning uchun unga
# egalik emas, faqat o'qish huquqi kifoya. .env esa maxfiy — uni bu
# rekursiv chmod'dan butunlay chetlab o'tamiz (find -prune), aks holda
# .env bir lahzaga ham bo'lsa hammaga o'qishli bo'lib qolardi (avval
# o'ziga, keyin chmod 640 bilan tor qilinguncha).
$SUDO find "$APP_DIR" -path "$BOT_DIR/.env" -prune -o -exec chmod o+rX {} +
$SUDO chgrp "$SERVICE_USER" "$BOT_DIR/.env"
$SUDO chmod 640 "$BOT_DIR/.env"

$SUDO cp "$APP_DIR/deploy/davomat.service" /etc/systemd/system/
$SUDO cp "$APP_DIR/deploy/davomat-api.service" /etc/systemd/system/
$SUDO systemctl daemon-reload
$SUDO systemctl enable --quiet --now davomat
$SUDO systemctl restart davomat
$SUDO systemctl enable --quiet --now davomat-api
$SUDO systemctl restart davomat-api

sleep 5
if $SUDO systemctl is-active --quiet davomat; then
  log "Tayyor: bot ishlayapti."
else
  echo "XATO: davomat xizmati ishga tushmadi. Sabab:"
  $SUDO journalctl -u davomat -n 30 --no-pager
  exit 1
fi

if $SUDO systemctl is-active --quiet davomat-api; then
  log "Tayyor: Mini App API ishlayapti."
else
  echo "XATO: davomat-api xizmati ishga tushmadi. Sabab:"
  $SUDO journalctl -u davomat-api -n 30 --no-pager
  exit 1
fi
