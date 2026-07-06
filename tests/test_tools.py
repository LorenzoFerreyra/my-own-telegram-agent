"""Tests for the pure/no-network paths in tools.py."""

from config import (
    ENTRADA_CATEGORIES,
    ENTRADA_PAYMENT_METHODS,
    VENTAS_CATEGORIES,
    VENTAS_PAYMENT_METHODS,
)
from tools import _fuzzy_match, add_expense, add_income


# ── _fuzzy_match ───────────────────────────────────────────────────

def test_fuzzy_match_exact_case_insensitive():
    assert _fuzzy_match("efectivo", ENTRADA_PAYMENT_METHODS) == "Efectivo"


def test_fuzzy_match_prefix():
    # "Alimentación (comestibles, restaurantes)" starts with "aliment"
    result = _fuzzy_match("aliment", ENTRADA_CATEGORIES)
    assert result is not None
    assert result.startswith("Alimentación")


def test_fuzzy_match_contains():
    # "comestibles" is inside the alimentacion label but not at the start
    result = _fuzzy_match("comestibles", ENTRADA_CATEGORIES)
    assert result is not None
    assert "comestibles" in result.lower()


def test_fuzzy_match_no_match_returns_none():
    assert _fuzzy_match("banana-empanada", ENTRADA_CATEGORIES) is None


def test_fuzzy_match_strips_whitespace():
    assert _fuzzy_match("  efectivo  ", ENTRADA_PAYMENT_METHODS) == "Efectivo"


def test_fuzzy_match_exact_wins_over_prefix():
    """A shorter valid entry that is an exact match must beat a longer one it prefixes."""
    valid = ["Cripto", "CriptoLargo"]
    assert _fuzzy_match("cripto", valid) == "Cripto"


# ── add_expense / add_income: input-validation branches ────────────
# These return before any gspread call, so they don't need mocks.

def test_add_expense_rejects_invalid_category():
    msg = add_expense.invoke(
        {
            "amount": 100,
            "description": "test",
            "category": "categoria-inventada-xyz",
            "payment_method": "Efectivo",
        }
    )
    assert "no válida" in msg
    assert "categoria-inventada-xyz" in msg


def test_add_expense_rejects_invalid_payment_method():
    msg = add_expense.invoke(
        {
            "amount": 100,
            "description": "test",
            "category": "Alimentación",
            "payment_method": "metodo-inventado-xyz",
        }
    )
    assert "no válido" in msg
    assert "metodo-inventado-xyz" in msg


def test_add_income_rejects_invalid_category():
    msg = add_income.invoke(
        {
            "amount": 100,
            "description": "test",
            "category": "categoria-inventada-xyz",
            "payment_method": "Efectivo",
        }
    )
    assert "no válida" in msg


def test_add_income_rejects_invalid_payment_method():
    msg = add_income.invoke(
        {
            "amount": 100,
            "description": "test",
            "category": "Salario",
            "payment_method": "metodo-inventado-xyz",
        }
    )
    assert "no válido" in msg


def test_error_lists_only_the_valid_options_for_that_sheet():
    """The message for an invalid income payment should not leak Ventas-only methods
    into an expense error and vice versa."""
    expense_err = add_expense.invoke(
        {
            "amount": 1,
            "description": "x",
            "category": "Alimentación",
            "payment_method": "nope",
        }
    )
    for method in ENTRADA_PAYMENT_METHODS:
        assert method in expense_err

    income_err = add_income.invoke(
        {
            "amount": 1,
            "description": "x",
            "category": "Salario",
            "payment_method": "nope",
        }
    )
    for method in VENTAS_PAYMENT_METHODS:
        assert method in income_err
    # QR is Entrada-only; it shouldn't show up in the income error
    assert "QR" not in income_err


def test_categories_lists_are_disjoint_enough_for_errors():
    """Sanity check on the config module the tests above depend on."""
    assert "Salario" in VENTAS_CATEGORIES
    assert "Salario" not in ENTRADA_CATEGORIES
