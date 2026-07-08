"""Tests for the pure/no-network paths in tools.py."""

import pytest

from config import (
    ENTRADA_CATEGORIES,
    ENTRADA_PAYMENT_METHODS,
    VENTAS_CATEGORIES,
    VENTAS_PAYMENT_METHODS,
)
import tools
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
    with pytest.raises(ValueError, match="no válida"):
        add_expense.invoke(
            {
                "amount": 100,
                "description": "test",
                "category": "categoria-inventada-xyz",
                "payment_method": "Efectivo",
            }
        )


def test_add_expense_rejects_invalid_payment_method():
    with pytest.raises(ValueError, match="no válido"):
        add_expense.invoke(
            {
                "amount": 100,
                "description": "test",
                "category": "Alimentación",
                "payment_method": "metodo-inventado-xyz",
            }
        )


def test_add_expense_rejects_blank_description():
    with pytest.raises(ValueError, match="descripción"):
        add_expense.invoke(
            {
                "amount": 100,
                "description": "   ",
                "category": "Alimentación",
                "payment_method": "Efectivo",
            }
        )


def test_add_expense_rejects_non_positive_amount():
    with pytest.raises(ValueError, match="mayor que cero"):
        add_expense.invoke(
            {
                "amount": 0,
                "description": "test",
                "category": "Alimentación",
                "payment_method": "Efectivo",
            }
        )


def test_add_income_rejects_invalid_category():
    with pytest.raises(ValueError, match="no válida"):
        add_income.invoke(
            {
                "amount": 100,
                "description": "test",
                "category": "categoria-inventada-xyz",
                "payment_method": "Efectivo",
            }
        )


def test_add_income_rejects_invalid_payment_method():
    with pytest.raises(ValueError, match="no válido"):
        add_income.invoke(
            {
                "amount": 100,
                "description": "test",
                "category": "Salario",
                "payment_method": "metodo-inventado-xyz",
            }
        )


def test_add_income_rejects_blank_description():
    with pytest.raises(ValueError, match="descripción"):
        add_income.invoke(
            {
                "amount": 100,
                "description": "   ",
                "category": "Salario",
                "payment_method": "Efectivo",
            }
        )


def test_add_income_rejects_negative_amount():
    with pytest.raises(ValueError, match="mayor que cero"):
        add_income.invoke(
            {
                "amount": -1,
                "description": "test",
                "category": "Salario",
                "payment_method": "Efectivo",
            }
        )


def test_error_lists_only_the_valid_options_for_that_sheet():
    """The message for an invalid income payment should not leak Ventas-only methods
    into an expense error and vice versa."""
    with pytest.raises(ValueError) as expense_exc:
        add_expense.invoke(
            {
                "amount": 1,
                "description": "x",
                "category": "Alimentación",
                "payment_method": "nope",
            }
        )
    expense_err = str(expense_exc.value)
    for method in ENTRADA_PAYMENT_METHODS:
        assert method in expense_err

    with pytest.raises(ValueError) as income_exc:
        add_income.invoke(
            {
                "amount": 1,
                "description": "x",
                "category": "Salario",
                "payment_method": "nope",
            }
        )
    income_err = str(income_exc.value)
    for method in VENTAS_PAYMENT_METHODS:
        assert method in income_err
    # QR is Entrada-only; it shouldn't show up in the income error
    assert "QR" not in income_err


def test_add_expense_keeps_transaction_when_report_fails(monkeypatch):
    class DummyWorksheet:
        def __init__(self):
            self.rows = []

        def append_row(self, row, value_input_option=None):
            self.rows.append((row, value_input_option))

    class DummySpreadsheet:
        def __init__(self):
            self.worksheet_obj = DummyWorksheet()

        def worksheet(self, name):
            return self.worksheet_obj

    class DummyClient:
        def __init__(self):
            self.spreadsheet = DummySpreadsheet()

        def open_by_key(self, sheet_id):
            return self.spreadsheet

    dummy_client = DummyClient()
    monkeypatch.setattr(tools, "get_gspread_client", lambda: dummy_client)

    class DummyReportTool:
        def invoke(self, payload):
            return "Error generando reporte: boom"

    monkeypatch.setattr(tools, "generate_monthly_report", DummyReportTool())

    msg = add_expense.invoke(
        {
            "amount": 100,
            "description": "test",
            "category": "Alimentación",
            "payment_method": "Efectivo",
        }
    )

    assert "registrado" in msg
    assert "no se pudo generar el reporte mensual" in msg.lower()
    assert dummy_client.spreadsheet.worksheet_obj.rows


def test_add_income_raises_when_append_fails(monkeypatch):
    class DummyWorksheet:
        def append_row(self, row, value_input_option=None):
            raise RuntimeError("sheet down")

    class DummySpreadsheet:
        def worksheet(self, name):
            return DummyWorksheet()

    class DummyClient:
        def open_by_key(self, sheet_id):
            return DummySpreadsheet()

    dummy_client = DummyClient()
    monkeypatch.setattr(tools, "get_gspread_client", lambda: dummy_client)
    called = {"report": False}

    class DummyReportTool:
        def invoke(self, _payload):
            called["report"] = True
            return "Balance del mes:\nIngresos: $0.00 | Gastos: $0.00\nTotal disponible: $0.00"

    monkeypatch.setattr(tools, "generate_monthly_report", DummyReportTool())

    with pytest.raises(RuntimeError, match="No se pudo registrar el ingreso"):
        add_income.invoke(
            {
                "amount": 100,
                "description": "test",
                "category": "Salario",
                "payment_method": "Efectivo",
            }
        )

    assert called["report"] is False


def test_categories_lists_are_disjoint_enough_for_errors():
    """Sanity check on the config module the tests above depend on."""
    assert "Salario" in VENTAS_CATEGORIES
    assert "Salario" not in ENTRADA_CATEGORIES
