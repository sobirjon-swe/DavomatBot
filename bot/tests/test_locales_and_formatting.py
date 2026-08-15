import ast
import pathlib
import re
from datetime import datetime, timezone

from locales import ru, t, uz
from utils.formatters import esc, format_datetime, format_user_districts
from utils.messages import text_of

BOT_DIR = pathlib.Path(__file__).resolve().parent.parent
PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


def _keys(module) -> set[str]:
    return {name for name in vars(module) if not name.startswith("_")}


def _used_keys() -> dict[str, set[str]]:
    """Kodda `t(lang, "kalit")` ko'rinishida ishlatilgan barcha kalitlar."""
    found: dict[str, set[str]] = {}
    for path in BOT_DIR.rglob("*.py"):
        if "alembic" in path.parts or "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            is_t_call = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "t"
                and len(node.args) >= 2
            )
            if not is_t_call:
                continue
            # Kalit shartli ifoda ham bo'lishi mumkin, shuning uchun ost-daraxt
            for const in ast.walk(node.args[1]):
                if isinstance(const, ast.Constant) and isinstance(const.value, str):
                    found.setdefault(const.value, set()).add(path.name)
    return found


# ─── Tarjimalar ─────────────────────────────────────────────────────────────

def test_kodda_ishlatilgan_barcha_kalitlar_mavjud():
    yoq = {k: sorted(v) for k, v in _used_keys().items() if k not in _keys(uz)}

    assert yoq == {}, f"uz.py da yo'q kalitlar: {yoq}"


def test_uz_va_ru_kalitlari_bir_xil():
    assert _keys(uz) == _keys(ru)


def test_placeholderlar_ikki_tilda_mos():
    """Tarjimada {min} kabi o'rin tushib qolsa, xabar noto'g'ri chiqadi
    yoki formatlash xatosi beradi."""
    farqlar = {}
    for key in _keys(uz):
        uz_val, ru_val = getattr(uz, key), getattr(ru, key)
        if not isinstance(uz_val, str) or not isinstance(ru_val, str):
            continue
        if set(PLACEHOLDER.findall(uz_val)) != set(PLACEHOLDER.findall(ru_val)):
            farqlar[key] = (
                sorted(set(PLACEHOLDER.findall(uz_val))),
                sorted(set(PLACEHOLDER.findall(ru_val))),
            )

    assert farqlar == {}, f"placeholderlar mos emas: {farqlar}"


def test_nomalum_til_ozbekchaga_qaytadi():
    assert t("de", "main_menu") == uz.main_menu


def test_nomalum_kalit_yiqilmaydi():
    assert t("uz", "umuman_yoq_kalit") == "umuman_yoq_kalit"


def test_yetishmayotgan_argument_xabarni_buzmaydi():
    """Formatlash xatosi butun handlerni yiqitmasligi kerak."""
    natija = t("uz", "wrong_password")

    assert isinstance(natija, str)


# ─── Formatlash ─────────────────────────────────────────────────────────────

def test_html_belgilari_ekranlanadi():
    """Regressiya: buyurtmachi nomida `<` yoki `&` bo'lsa Telegram xabarni
    umuman yubormay qo'yardi."""
    assert esc("Ali & Vali <OOO>") == "Ali &amp; Vali &lt;OOO&gt;"


def test_ekranlash_oddiy_matnga_tegmaydi():
    assert esc("Toshkent shahar") == "Toshkent shahar"


def test_vaqt_toshkent_mintaqasida_korsatiladi():
    utc_vaqt = datetime(2026, 6, 5, 6, 30, tzinfo=timezone.utc)

    assert format_datetime(utc_vaqt) == "05.06.2026 | 11:30"


def test_eski_naive_vaqt_utc_deb_qabul_qilinadi():
    """Migratsiyagacha yozilgan qatorlar vaqt mintaqasiz bo'lishi mumkin."""
    naive = datetime(2026, 6, 5, 6, 30)

    assert format_datetime(naive) == "05.06.2026 | 11:30"


def test_tumansiz_hodim_uchun_chiziqcha():
    assert format_user_districts([], "uz") == "—"


# ─── Xabar yordamchisi ──────────────────────────────────────────────────────

class _FakeMessage:
    def __init__(self, text):
        self.text = text


def test_matn_kesiladi():
    assert text_of(_FakeMessage("  Ali Valiyev  ")) == "Ali Valiyev"


def test_matnsiz_xabar_none_qaytaradi():
    """Regressiya: matn kutilgan joyda rasm yuborilsa
    `message.text.strip()` AttributeError bilan yiqilardi."""
    assert text_of(_FakeMessage(None)) is None
