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
PYTHON="${PYTHON:-python3.11}"

DB_NAME="${DB_NAME:-davomat_db}"
DB_USER="${DB_USER:-davomat}"
SERVICE_USER="${SERVICE_USER:-davomat}"

log() { printf '\n==> %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# ─── 1. Tizim paketlari ─────────────────────────────────────────────────────

log "Tizim paketlari"
NEED_PG=1
[ -n "${DATABASE_URL:-}" ] && NEED_PG=0

if ! have "$PYTHON" || ! have git || { [ "$NEED_PG" = "1" ] && ! have psql; }; then
  $SUDO apt-get update -qq
  PACKAGES="$PYTHON $PYTHON-venv git"
  [ "$NEED_PG" = "1" ] && PACKAGES="$PACKAGES postgresql"
  # shellcheck disable=SC2086
  $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $PACKAGES
else
  echo "Kerakli paketlar allaqachon bor."
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

# ─── 7. Xizmat ──────────────────────────────────────────────────────────────

log "systemd xizmati"
id -u "$SERVICE_USER" >/dev/null 2>&1 \
  || $SUDO useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"

$SUDO chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
$SUDO cp "$APP_DIR/deploy/davomat.service" /etc/systemd/system/
$SUDO systemctl daemon-reload
$SUDO systemctl enable --quiet --now davomat
$SUDO systemctl restart davomat

sleep 5
if $SUDO systemctl is-active --quiet davomat; then
  log "Tayyor: bot ishlayapti."
else
  echo "XATO: xizmat ishga tushmadi. Sabab:"
  $SUDO journalctl -u davomat -n 30 --no-pager
  exit 1
fi
