import pytest
from aiogram.types import MenuButtonCommands, MenuButtonWebApp

import config
from keyboards import webapp
from keyboards.admin_kb import admin_main_menu_kb
from keyboards.employee_kb import main_menu_kb
from locales import t

APP_URL = "https://davomat.example.uz"


@pytest.fixture
def with_webapp(monkeypatch):
    monkeypatch.setattr(config, "WEBAPP_URL", APP_URL)


@pytest.fixture
def without_webapp(monkeypatch):
    monkeypatch.setattr(config, "WEBAPP_URL", "")


def _buttons(markup):
    return [button for row in markup.keyboard for button in row]


def _app_buttons(markup):
    return [b for b in _buttons(markup) if b.web_app is not None]


# ─── Sozlanmagan holat ──────────────────────────────────────────────────────

def test_url_siz_tugma_korsatilmaydi(without_webapp):
    """WEBAPP_URL bo'lmasa ishlamaydigan tugma chiqmasligi kerak."""
    assert webapp.is_enabled() is False
    assert webapp.reply_button("uz") is None
    assert webapp.inline_kb("uz") is None


def test_url_siz_menyu_buyruqlarga_qaytadi(without_webapp):
    """Eski Mini App tugmasi osilib qolmasligi uchun menyu tiklanadi."""
    assert isinstance(webapp.menu_button(), MenuButtonCommands)


def test_url_siz_asosiy_menyu_ozgarmaydi(without_webapp):
    markup = main_menu_kb("uz")

    assert _app_buttons(markup) == []
    assert len(_buttons(markup)) == 2


# ─── Sozlangan holat ────────────────────────────────────────────────────────

def test_menyu_tugmasi_ilovaga_ishora_qiladi(with_webapp):
    button = webapp.menu_button()

    assert isinstance(button, MenuButtonWebApp)
    assert button.web_app.url == APP_URL


def test_hodim_menyusida_ilova_tugmasi_bor(with_webapp):
    app_buttons = _app_buttons(main_menu_kb("uz"))

    assert len(app_buttons) == 1
    assert app_buttons[0].web_app.url == APP_URL
    assert app_buttons[0].text == t("uz", "btn_open_app")


def test_admin_menyusida_ilova_tugmasi_bor(with_webapp):
    markup = admin_main_menu_kb("uz", is_superadmin=True)

    assert len(_app_buttons(markup)) == 1
    # Mavjud tugmalar joyida qolishi kerak: 6 ta menyu + 1 ta ilova
    assert len(_buttons(markup)) == 7


def test_ruscha_tugma_tarjimasi(with_webapp):
    app_button = _app_buttons(main_menu_kb("ru"))[0]

    assert app_button.text == t("ru", "btn_open_app")


def test_inline_tugma(with_webapp):
    markup = webapp.inline_kb("uz")

    assert markup is not None
    assert markup.inline_keyboard[0][0].web_app.url == APP_URL


# ─── Konfiguratsiya tekshiruvi ──────────────────────────────────────────────

def test_https_bolmagan_manzil_rad_etiladi(monkeypatch):
    """Telegram Mini App shifrlanmagan manzilni ochmaydi — buni ishga
    tushishda ushlagan ma'qul, foydalanuvchi oldida emas."""
    monkeypatch.setenv("WEBAPP_URL", "http://davomat.example.uz")

    with pytest.raises(config.ConfigError):
        config._webapp_url("WEBAPP_URL")


def test_oxiridagi_slesh_olib_tashlanadi(monkeypatch):
    monkeypatch.setenv("WEBAPP_URL", "https://davomat.example.uz/")

    assert config._webapp_url("WEBAPP_URL") == APP_URL


def test_bosh_qiymat_xato_bermaydi(monkeypatch):
    monkeypatch.setenv("WEBAPP_URL", "")

    assert config._webapp_url("WEBAPP_URL") == ""
