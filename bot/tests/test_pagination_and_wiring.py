import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from keyboards.pagination import (
    PER_PAGE,
    clamp,
    list_page_kb,
    nav_row,
    offset_of,
    page_count,
    with_back_button,
)

# ─── Sahifa hisobi ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "total, kutilgan",
    [(0, 1), (1, 1), (PER_PAGE, 1), (PER_PAGE + 1, 2), (PER_PAGE * 3, 3)],
)
def test_sahifalar_soni(total, kutilgan):
    assert page_count(total) == kutilgan


def test_bosh_royxatda_ham_bitta_sahifa():
    """0 sahifa bo'lsa "1/0" kabi bema'ni ko'rsatkich chiqardi."""
    assert page_count(0) == 1


@pytest.mark.parametrize(
    "page, pages, kutilgan",
    [(0, 5, 1), (-3, 5, 1), (3, 5, 3), (9, 5, 5)],
)
def test_sahifa_chegaraga_solinadi(page, pages, kutilgan):
    """Eski xabardagi tugma bosilganda ro'yxat qisqargan bo'lishi mumkin."""
    assert clamp(page, pages) == kutilgan


def test_offset_hisobi():
    assert offset_of(1) == 0
    assert offset_of(3) == PER_PAGE * 2


# ─── Klaviatura ─────────────────────────────────────────────────────────────

def _callbacks(markup):
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def test_royxat_tugmalari_sahifani_eslab_qoladi():
    markup = list_page_kb(
        open_prefix="emp_card",
        page_prefix="emp_page",
        page=2,
        pages=3,
        items=[(7, "Ali"), (9, "Vali")],
    )

    assert "emp_card:7:2" in _callbacks(markup)
    assert "emp_card:9:2" in _callbacks(markup)


def test_bitta_sahifada_navigatsiya_korsatilmaydi():
    markup = list_page_kb(
        open_prefix="emp_card", page_prefix="emp_page",
        page=1, pages=1, items=[(1, "Ali")],
    )

    assert all(not cb.startswith("emp_page:") for cb in _callbacks(markup))


def test_birinchi_sahifada_orqaga_ishlamaydi():
    row = nav_row("emp_page", page=1, pages=3)

    # ["◀️ (o'chiq)", "1/3 (o'chiq)", "▶️"]
    assert [b.callback_data for b in row] == ["noop", "noop", "emp_page:2"]


def test_oxirgi_sahifada_oldinga_ishlamaydi():
    row = nav_row("emp_page", page=3, pages=3)

    assert [b.callback_data for b in row] == ["emp_page:2", "noop", "noop"]


def test_ortadagi_sahifada_ikkala_yonalish_ishlaydi():
    row = nav_row("emp_page", page=2, pages=3)

    assert [b.callback_data for b in row] == ["emp_page:1", "noop", "emp_page:3"]


def test_qaytish_tugmasi_mavjud_tugmalarni_saqlaydi():
    ichki = list_page_kb(
        open_prefix="x", page_prefix="y", page=1, pages=1, items=[(1, "Bitta")]
    )

    markup = with_back_button("uz", "emp_page", 4, ichki)

    assert "x:1:1" in _callbacks(markup)
    assert "emp_page:4" in _callbacks(markup)


# ─── Routerlar ulanishi ─────────────────────────────────────────────────────

def test_dispatcher_barcha_routerlar_bilan_yigiladi():
    """Import xatosi yoki takroriy ro'yxatga olish shu yerda ushlanadi."""
    import main
    from middlewares.auth import AuthMiddleware

    dp = Dispatcher(storage=MemoryStorage())
    auth = AuthMiddleware()
    dp.message.outer_middleware(auth)
    dp.callback_query.outer_middleware(auth)
    dp.errors.register(main.on_error)

    for router in (
        main.start_router,
        main.report_router,
        main.settings_router,
        main.employees_router,
        main.admin_reports_router,
        main.attendance_router,
        main.password_router,
        main.roles_router,
    ):
        dp.include_router(router)

    assert set(dp.resolve_used_update_types()) == {"message", "callback_query"}
