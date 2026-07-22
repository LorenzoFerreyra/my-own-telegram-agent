"""Module for Telegram agent tools, including expense and income management via Google Sheets."""

import os
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")
import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from langchain_core.tools import tool

from config import (
    ENTRADA_CATEGORIES,
    ENTRADA_PAYMENT_METHODS,
    VENTAS_CATEGORIES,
    VENTAS_PAYMENT_METHODS,
)

load_dotenv()

# Filas de las planillas que pertenecen a este usuario (hay filas de otras
# automatizaciones en las mismas hojas).
KNOWN_USER_IDS = ["16162b8f", "3075a55c"]

MONTH_NAMES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Guardrail anti-duplicados: si el modelo llama a la misma tool con los mismos
# datos dentro de esta ventana, se ignora la segunda llamada en vez de crear
# otra fila en la planilla.
DEDUP_WINDOW_SECONDS = float(os.getenv("DEDUP_WINDOW_SECONDS", "120"))
_recent_transactions: dict[tuple[str, float, str], float] = {}


def _dedup_key(kind: str, amount: float, description: str) -> tuple[str, float, str]:
    return (kind, round(float(amount), 2), description.strip().lower())


def _is_recent_duplicate(kind: str, amount: float, description: str) -> bool:
    """True if an identical transaction was already recorded within the dedup window."""
    now = time.monotonic()
    for key, recorded_at in list(_recent_transactions.items()):
        if now - recorded_at > DEDUP_WINDOW_SECONDS:
            del _recent_transactions[key]
    return _dedup_key(kind, amount, description) in _recent_transactions


def _remember_transaction(kind: str, amount: float, description: str) -> None:
    _recent_transactions[_dedup_key(kind, amount, description)] = time.monotonic()


def _fuzzy_match(value: str, valid_list: list[str]) -> str | None:
    """Find the full valid entry that starts with or contains the given value (case-insensitive).
    Returns the matched full string, or None if no match found."""
    value_lower = value.strip().lower()
    # Exact match first
    for item in valid_list:
        if item.lower() == value_lower:
            return item
    # Prefix match
    for item in valid_list:
        if item.lower().startswith(value_lower):
            return item
    # Contains match
    for item in valid_list:
        if value_lower in item.lower():
            return item
    return None


def _validate_transaction_inputs(
    amount: float,
    description: str,
    category: str,
    payment_method: str,
    valid_categories: list[str],
    valid_payment_methods: list[str],
) -> tuple[float, str, str, str]:
    if amount is None or not isinstance(amount, (int, float)) or not pd.notna(amount):
        raise ValueError("El monto debe ser un número válido y mayor que cero.")
    if amount <= 0:
        raise ValueError("El monto debe ser mayor que cero.")

    description = description.strip()
    if not description:
        raise ValueError("La descripción no puede estar vacía.")

    matched_category = _fuzzy_match(category, valid_categories)
    if not matched_category:
        raise ValueError(
            f"Categoría '{category}' no válida. Usa: {', '.join(valid_categories)}"
        )

    matched_payment = _fuzzy_match(payment_method, valid_payment_methods)
    if not matched_payment:
        raise ValueError(
            f"Método '{payment_method}' no válido. Usa: {', '.join(valid_payment_methods)}"
        )

    return float(amount), description, matched_category, matched_payment


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Falta la variable de entorno obligatoria: {name}")
    return value


def get_gspread_client():
    """Initialize and return a gspread client"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_file = _get_required_env("GOOGLE_APPLICATION_CREDENTIALS")
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    return gspread.authorize(creds)


@tool
def add_expense(
    amount: float, description: str, category: str, payment_method: str = "Efectivo"
) -> str:
    """Add an expense to EntradaMaterial sheet.

    Args:
        amount: The amount spent (positive number)
        description: What the expense was for
        category: Category from your sheet (e.g., Alimentación, Transporte, Vivienda, etc.)
        payment_method: Payment method from your sheet (e.g., Efectivo, Tarjeta de crédito, Transferencia, etc.)

    Returns:
        Confirmation message
    """

    amount, description, category, payment_method = _validate_transaction_inputs(
        amount,
        description,
        category,
        payment_method,
        ENTRADA_CATEGORIES,
        ENTRADA_PAYMENT_METHODS,
    )

    if _is_recent_duplicate("expense", amount, description):
        return (
            f"Ese gasto de ${amount:g} en {description} ya fue registrado hace un momento. "
            "No lo registré de nuevo para evitar duplicados. La operación ya está guardada."
        )

    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(_get_required_env("GOOGLE_SHEET_ID"))
        worksheet = spreadsheet.worksheet("EntradaMaterial")

        now = datetime.now(ARGENTINA)
        row = [
            uuid.uuid4().hex[:8],
            now.strftime("%d/%m/%Y"),
            now.strftime("%d/%m/%Y %H:%M:%S"),
            "16162b8f",
            "TRUE",
            abs(amount),
            category,
            description,
            payment_method,
        ]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        _remember_transaction("expense", amount, description)
        report = generate_monthly_report.invoke({})
        if report.startswith("Error generando reporte:"):
            return (
                f"Gasto de ${amount:g} en {description} registrado (categoría: {category}, pago: {payment_method}).\n\n"
                f"Aviso: no se pudo generar el reporte mensual. {report}"
            )
        return (
            f"Gasto de ${amount:g} en {description} registrado (categoría: {category}, pago: {payment_method}).\n\n"
            f"{report}"
        )
    except Exception as e:
        raise RuntimeError(f"No se pudo registrar el gasto: {str(e)}") from e


@tool
def add_income(
    amount: float, description: str, category: str, payment_method: str = "Efectivo"
) -> str:
    """Add income to Ventas sheet.

    Args:
        amount: The amount received (positive number)
        description: What the income was for
        category: Category from your sheet (e.g., Salario, Freelance, Emprendimiento, etc.)
        payment_method: Payment method from your sheet (e.g., Efectivo, Tarjeta de débito, Transferencia, etc.)

    Returns:
        Confirmation message
    """

    amount, description, category, payment_method = _validate_transaction_inputs(
        amount,
        description,
        category,
        payment_method,
        VENTAS_CATEGORIES,
        VENTAS_PAYMENT_METHODS,
    )

    if _is_recent_duplicate("income", amount, description):
        return (
            f"Ese ingreso de ${amount:g} por {description} ya fue registrado hace un momento. "
            "No lo registré de nuevo para evitar duplicados. La operación ya está guardada."
        )

    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(_get_required_env("GOOGLE_SHEET_ID"))
        worksheet = spreadsheet.worksheet("Ventas")

        now = datetime.now(ARGENTINA)
        row = [
            uuid.uuid4().hex[:8],
            now.strftime("%d/%m/%Y"),
            now.strftime("%d/%m/%Y %H:%M:%S"),
            "16162b8f",
            payment_method,
            "TRUE",
            description,
            abs(amount),
            category,
        ]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        _remember_transaction("income", amount, description)
        report = generate_monthly_report.invoke({})
        if report.startswith("Error generando reporte:"):
            return (
                f"Ingreso de ${amount:g} por {description} registrado (categoría: {category}, pago: {payment_method}).\n\n"
                f"Aviso: no se pudo generar el reporte mensual. {report}"
            )
        return (
            f"Ingreso de ${amount:g} por {description} registrado (categoría: {category}, pago: {payment_method}).\n\n"
            f"{report}"
        )
    except Exception as e:
        raise RuntimeError(f"No se pudo registrar el ingreso: {str(e)}") from e


# ── reporting helpers ───────────────────────────────────────────────


def _resolve_month(month: int | None, year: int | None) -> tuple[int, int]:
    """Fill in missing month/year with the current date in Argentina."""
    now = datetime.now(ARGENTINA)
    month = month if month is not None else now.month
    year = year if year is not None else now.year
    if not 1 <= month <= 12:
        raise ValueError("El mes debe estar entre 1 y 12.")
    return month, year


def _month_label(month: int, year: int) -> str:
    return f"{MONTH_NAMES_ES[month - 1]} {year}"


def _short_category(category: str) -> str:
    """'Alimentación (comestibles, restaurantes)' -> 'Alimentación'."""
    return str(category).split(" (")[0]


def _load_transactions(
    spreadsheet, worksheet_name: str, date_column: str, extra_columns: tuple = ()
) -> pd.DataFrame:
    """Read a worksheet into a DataFrame ready for reporting: Monto as numbers,
    dates parsed, and only the rows that belong to the known users."""
    df = pd.DataFrame(spreadsheet.worksheet(worksheet_name).get_all_records())
    if df.empty:
        return df

    required = {"Monto", date_column, "UsuarioID", *extra_columns}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas en la hoja {worksheet_name}: {', '.join(sorted(missing))}"
        )

    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce")
    df[date_column] = pd.to_datetime(
        df[date_column], format="%d/%m/%Y", errors="coerce"
    )
    return df[df["UsuarioID"].isin(KNOWN_USER_IDS)]


def _month_rows(df: pd.DataFrame, date_column: str, month: int, year: int) -> pd.DataFrame:
    """Rows of df that fall inside the given month."""
    if df.empty:
        return df
    dates = df[date_column]
    return df[(dates.dt.year == year) & (dates.dt.month == month)]


def _month_total(df: pd.DataFrame, date_column: str, month: int, year: int) -> float:
    """Sum of Monto for the given month; 0.0 when there are no rows."""
    rows = _month_rows(df, date_column, month, year)
    return 0.0 if rows.empty else float(rows["Monto"].sum())


@tool
def generate_monthly_report(month: int | None = None, year: int | None = None) -> str:
    """Generate a balance report: total income minus total expenses for one month.

    Args:
        month: Month to report, 1-12. Defaults to the current month.
        year: Four-digit year. Defaults to the current year.

    Returns:
        A string message with the balance summary.
    """
    try:
        month, year = _resolve_month(month, year)
        client = get_gspread_client()
        spreadsheet = client.open_by_key(_get_required_env("GOOGLE_SHEET_ID"))

        ventas = _load_transactions(spreadsheet, "Ventas", "VentaFecha")
        gastos = _load_transactions(spreadsheet, "EntradaMaterial", "EntradaMaterialFecha")

        total_income = _month_total(ventas, "VentaFecha", month, year)
        total_expenses = _month_total(gastos, "EntradaMaterialFecha", month, year)
        balance = total_income - total_expenses

        return (
            f"Balance de {_month_label(month, year)}:\n"
            f"Ingresos: ${total_income:,.2f} | Gastos: ${total_expenses:,.2f}\n"
            f"Total disponible: ${balance:,.2f}"
        )
    except Exception as e:
        return f"Error generando reporte: {str(e)}"


@tool
def spending_by_category(month: int | None = None, year: int | None = None) -> str:
    """Break down one month's expenses by category, biggest first.

    Args:
        month: Month to analyze, 1-12. Defaults to the current month.
        year: Four-digit year. Defaults to the current year.

    Returns:
        A string with one line per category, sorted by amount spent.
    """
    try:
        month, year = _resolve_month(month, year)
        client = get_gspread_client()
        spreadsheet = client.open_by_key(_get_required_env("GOOGLE_SHEET_ID"))

        gastos = _load_transactions(
            spreadsheet, "EntradaMaterial", "EntradaMaterialFecha",
            extra_columns=("Categoria",),
        )
        month_expenses = _month_rows(gastos, "EntradaMaterialFecha", month, year)
        if month_expenses.empty:
            return f"No hay gastos registrados en {_month_label(month, year)}."

        totals = (
            month_expenses.groupby("Categoria")["Monto"].sum().sort_values(ascending=False)
        )
        grand_total = totals.sum()

        lines = [f"Gastos por categoría en {_month_label(month, year)}:"]
        for category, amount in totals.items():
            share = amount / grand_total * 100
            lines.append(f"- {_short_category(category)}: ${amount:,.2f} ({share:.0f}%)")
        lines.append(f"Total: ${grand_total:,.2f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error generando desglose: {str(e)}"


@tool
def list_recent_transactions(limit: int = 10) -> str:
    """List the most recent transactions, expenses and incomes combined.

    Args:
        limit: How many transactions to show, most recent first (default 10).

    Returns:
        A string with one line per transaction.
    """
    try:
        if limit <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")

        client = get_gspread_client()
        spreadsheet = client.open_by_key(_get_required_env("GOOGLE_SHEET_ID"))

        gastos = _load_transactions(
            spreadsheet, "EntradaMaterial", "EntradaMaterialFecha",
            extra_columns=("Notas", "Categoria"),
        )
        ventas = _load_transactions(
            spreadsheet, "Ventas", "VentaFecha",
            extra_columns=("VentaNotas", "Categoria"),
        )

        entries = []
        for _, row in gastos.iterrows():
            entries.append(
                (row["EntradaMaterialFecha"], "Gasto", row["Monto"], row["Notas"], row["Categoria"])
            )
        for _, row in ventas.iterrows():
            entries.append(
                (row["VentaFecha"], "Ingreso", row["Monto"], row["VentaNotas"], row["Categoria"])
            )

        entries = [e for e in entries if pd.notna(e[0])]
        if not entries:
            return "No hay movimientos registrados todavía."

        entries.sort(key=lambda e: e[0], reverse=True)
        shown = entries[:limit]

        lines = [f"Últimos {len(shown)} movimientos:"]
        for when, kind, amount, note, category in shown:
            lines.append(
                f"- {when.strftime('%d/%m/%Y')} | {kind} | ${amount:,.2f} | "
                f"{note} ({_short_category(category)})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listando movimientos: {str(e)}"
