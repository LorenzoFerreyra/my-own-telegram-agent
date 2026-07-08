"""Module for Telegram agent tools, including expense and income management via Google Sheets."""

import os
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


@tool
def generate_monthly_report() -> str:
    """Generate a monthly balance report: total income minus total expenses for the current month.

    Returns:
        A string message with the balance summary.
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(_get_required_env("GOOGLE_SHEET_ID"))

        ventas_sheet = spreadsheet.worksheet("Ventas")
        ventas_data = ventas_sheet.get_all_records()
        df_ventas = pd.DataFrame(ventas_data)
        if not df_ventas.empty:
            required_ventas_columns = {"Monto", "VentaFecha", "UsuarioID"}
            missing_ventas_columns = required_ventas_columns - set(df_ventas.columns)
            if missing_ventas_columns:
                raise ValueError(
                    f"Faltan columnas en la hoja Ventas: {', '.join(sorted(missing_ventas_columns))}"
                )
            df_ventas["Monto"] = pd.to_numeric(df_ventas["Monto"], errors="coerce")
            df_ventas["VentaFecha"] = pd.to_datetime(
                df_ventas["VentaFecha"], format="%d/%m/%Y", errors="coerce"
            )
            filtered_ventas = df_ventas[
                (df_ventas["VentaFecha"].dt.year == datetime.now(ARGENTINA).year)
                & (df_ventas["VentaFecha"].dt.month == datetime.now(ARGENTINA).month)
                & (df_ventas["UsuarioID"].isin(["16162b8f", "3075a55c"]))
            ]
            total_income = filtered_ventas["Monto"].sum()
        else:
            total_income = 0.0

        gastos_sheet = spreadsheet.worksheet("EntradaMaterial")
        gastos_data = gastos_sheet.get_all_records()
        df_gastos = pd.DataFrame(gastos_data)
        if not df_gastos.empty:
            required_gastos_columns = {"Monto", "EntradaMaterialFecha", "UsuarioID"}
            missing_gastos_columns = required_gastos_columns - set(df_gastos.columns)
            if missing_gastos_columns:
                raise ValueError(
                    f"Faltan columnas en la hoja EntradaMaterial: {', '.join(sorted(missing_gastos_columns))}"
                )
            df_gastos["Monto"] = pd.to_numeric(df_gastos["Monto"], errors="coerce")
            df_gastos["EntradaMaterialFecha"] = pd.to_datetime(
                df_gastos["EntradaMaterialFecha"], format="%d/%m/%Y", errors="coerce"
            )
            filtered_gastos = df_gastos[
                (
                    df_gastos["EntradaMaterialFecha"].dt.year
                    == datetime.now(ARGENTINA).year
                )
                & (
                    df_gastos["EntradaMaterialFecha"].dt.month
                    == datetime.now(ARGENTINA).month
                )
                & (df_gastos["UsuarioID"].isin(["16162b8f", "3075a55c"]))
            ]
            total_expenses = filtered_gastos["Monto"].sum()
        else:
            total_expenses = 0.0

        balance = total_income - total_expenses
        message = (
            f"Balance del mes:\n"
            f"Ingresos: ${total_income:.2f} | Gastos: ${total_expenses:.2f}\n"
            f"Total disponible: ${balance:.2f}"
        )
        return message
    except Exception as e:
        return f"Error generando reporte: {str(e)}"
