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


# ── anti-duplicate guardrail ────────────────────────────────────────

class _DummyWorksheet:
    def __init__(self):
        self.rows = []

    def append_row(self, row, value_input_option=None):
        self.rows.append(row)


class _DummySpreadsheet:
    def __init__(self):
        self.worksheet_obj = _DummyWorksheet()

    def worksheet(self, name):
        return self.worksheet_obj


class _DummyClient:
    def __init__(self):
        self.spreadsheet = _DummySpreadsheet()

    def open_by_key(self, sheet_id):
        return self.spreadsheet


class _DummyReportTool:
    def invoke(self, _payload):
        return "Balance del mes:\nIngresos: $0.00 | Gastos: $0.00\nTotal disponible: $0.00"


@pytest.fixture
def sheets(monkeypatch):
    """Patch gspread + report so add_expense/add_income run fully offline."""
    client = _DummyClient()
    monkeypatch.setattr(tools, "get_gspread_client", lambda: client)
    monkeypatch.setattr(tools, "generate_monthly_report", _DummyReportTool())
    return client.spreadsheet.worksheet_obj


_EXPENSE = {
    "amount": 5000,
    "description": "pizza",
    "category": "Alimentación",
    "payment_method": "Efectivo",
}


def test_repeated_expense_within_window_is_not_recorded_twice(sheets):
    first = add_expense.invoke(_EXPENSE)
    second = add_expense.invoke(_EXPENSE)

    assert "registrado" in first
    assert "ya fue registrado" in second
    assert len(sheets.rows) == 1


def test_repeated_income_within_window_is_not_recorded_twice(sheets):
    payload = {
        "amount": 30000,
        "description": "venta remera",
        "category": "Salario",
        "payment_method": "Efectivo",
    }
    add_income.invoke(payload)
    second = add_income.invoke(payload)

    assert "ya fue registrado" in second
    assert len(sheets.rows) == 1


def test_dedup_ignores_description_case_and_whitespace(sheets):
    add_expense.invoke(_EXPENSE)
    second = add_expense.invoke({**_EXPENSE, "description": "  PIZZA "})

    assert "ya fue registrado" in second
    assert len(sheets.rows) == 1


def test_different_amount_is_a_new_transaction(sheets):
    add_expense.invoke(_EXPENSE)
    second = add_expense.invoke({**_EXPENSE, "amount": 7000})

    assert "registrado" in second
    assert "ya fue registrado" not in second
    assert len(sheets.rows) == 2


def test_expense_and_income_do_not_share_dedup_keys(sheets):
    add_expense.invoke(_EXPENSE)
    income = add_income.invoke(
        {
            "amount": 5000,
            "description": "pizza",
            "category": "Salario",
            "payment_method": "Efectivo",
        }
    )

    assert "ya fue registrado" not in income
    assert len(sheets.rows) == 2


def test_dedup_expires_after_window(sheets, monkeypatch):
    add_expense.invoke(_EXPENSE)

    # Pretend the dedup window already elapsed
    real_monotonic = tools.time.monotonic
    monkeypatch.setattr(
        tools.time,
        "monotonic",
        lambda: real_monotonic() + tools.DEDUP_WINDOW_SECONDS + 1,
    )

    second = add_expense.invoke(_EXPENSE)
    assert "ya fue registrado" not in second
    assert len(sheets.rows) == 2


def test_failed_append_does_not_block_retry(monkeypatch):
    """If the sheet write fails, the transaction must NOT be remembered as recorded."""
    calls = {"n": 0}

    class FlakyWorksheet:
        def __init__(self):
            self.rows = []

        def append_row(self, row, value_input_option=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("sheet down")
            self.rows.append(row)

    worksheet = FlakyWorksheet()

    class Spreadsheet:
        def worksheet(self, name):
            return worksheet

    class Client:
        def open_by_key(self, sheet_id):
            return Spreadsheet()

    monkeypatch.setattr(tools, "get_gspread_client", lambda: Client())
    monkeypatch.setattr(tools, "generate_monthly_report", _DummyReportTool())

    with pytest.raises(RuntimeError, match="No se pudo registrar el gasto"):
        add_expense.invoke(_EXPENSE)

    retry = add_expense.invoke(_EXPENSE)
    assert "ya fue registrado" not in retry
    assert len(worksheet.rows) == 1
