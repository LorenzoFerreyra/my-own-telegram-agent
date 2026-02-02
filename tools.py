"""Module for Telegram agent tools, including expense and income management via Google Sheets."""

import os
from datetime import datetime
import uuid
from langchain_core.tools import tool
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from config import (
    ENTRADA_CATEGORIES,
    ENTRADA_PAYMENT_METHODS,
    VENTAS_CATEGORIES,
    VENTAS_PAYMENT_METHODS,
)

load_dotenv()


def get_gspread_client():
    """Initialize and return a gspread client"""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    return gspread.authorize(creds)


@tool
def add_expense(amount: float, description: str, category: str, payment_method: str = "Efectivo") -> str:
    """Add an expense to EntradaMaterial sheet.
    
    Args:
        amount: The amount spent (positive number)
        description: What the expense was for
        category: Category from your sheet (e.g., Alimentación, Transporte, Vivienda, etc.)
        payment_method: Payment method from your sheet (e.g., Efectivo, Tarjeta de crédito, Transferencia, etc.)
    
    Returns:
        Confirmation message
    """
    
    if category not in ENTRADA_CATEGORIES:
        return f"Categoría '{category}' no válida. Usa: {', '.join(ENTRADA_CATEGORIES)}"
    if payment_method not in ENTRADA_PAYMENT_METHODS:
        return f"Método '{payment_method}' no válido. Usa: {', '.join(ENTRADA_PAYMENT_METHODS)}"
    
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID"))
        worksheet = spreadsheet.worksheet("EntradaMaterial")
        
        row = [
            uuid.uuid4().hex[:8],
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "16162b8f",
            "TRUE",
            abs(amount),
            category,
            description,
            payment_method
        ]
        worksheet.append_row(row)
        return f"Gasto registrado: ${amount} en {description} ({category}) por el bot"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def add_income(amount: float, description: str, category: str, payment_method: str = "Efectivo") -> str:
    """Add income to Ventas sheet.
    
    Args:
        amount: The amount received (positive number)
        description: What the income was for
        category: Category from your sheet (e.g., Salario, Freelance, Emprendimiento, etc.)
        payment_method: Payment method from your sheet (e.g., Efectivo, Tarjeta de débito, Transferencia, etc.)
    
    Returns:
        Confirmation message
    """
    
    # Validate
    if category not in VENTAS_CATEGORIES:
        return f"Categoría '{category}' no válida. Usa: {', '.join(VENTAS_CATEGORIES)}"
    if payment_method not in VENTAS_PAYMENT_METHODS:
        return f"Método '{payment_method}' no válido. Usa: {', '.join(VENTAS_PAYMENT_METHODS)}"
    
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID"))
        worksheet = spreadsheet.worksheet("Ventas")
        
        row = [
            uuid.uuid4().hex[:8],
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "16162b8f",
            payment_method,
            "TRUE",
            description,
            abs(amount),
            category
        ]
        worksheet.append_row(row)
        return f"Ingreso registrado: ${amount} de {description} ({category}) por el bot"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def generate_monthly_report() -> str:
    """Generate a monthly balance report: total income minus total expenses for the current month.
    
    Returns:
        A string message with the balance summary.
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID"))
        
        ventas_sheet = spreadsheet.worksheet("Ventas")
        ventas_data = ventas_sheet.get_all_records()
        df_ventas = pd.DataFrame(ventas_data)
        if not df_ventas.empty:
            df_ventas["Monto"] = pd.to_numeric(df_ventas["Monto"], errors="coerce")
            df_ventas["VentaFecha"] = pd.to_datetime(df_ventas["VentaFecha"], format="%d/%m/%Y", errors="coerce")
            filtered_ventas = df_ventas[
                (df_ventas["VentaFecha"].dt.year == datetime.now().year) &
                (df_ventas["VentaFecha"].dt.month == datetime.now().month) &
                (df_ventas["UsuarioID"].isin(["16162b8f", "3075a55c"]))
            ]
            total_income = filtered_ventas["Monto"].sum()
        else:
            total_income = 0.0
        
        gastos_sheet = spreadsheet.worksheet("EntradaMaterial")
        gastos_data = gastos_sheet.get_all_records()
        df_gastos = pd.DataFrame(gastos_data)
        if not df_gastos.empty:
            df_gastos["Monto"] = pd.to_numeric(df_gastos["Monto"], errors="coerce")
            df_gastos["EntradaMaterialFecha"] = pd.to_datetime(df_gastos["EntradaMaterialFecha"], format="%d/%m/%Y", errors="coerce")
            filtered_gastos = df_gastos[
                (df_gastos["EntradaMaterialFecha"].dt.year == datetime.now().year) &
                (df_gastos["EntradaMaterialFecha"].dt.month == datetime.now().month) &
                (df_gastos["UsuarioID"].isin(["16162b8f", "3075a55c"]))
            ]
            total_expenses = filtered_gastos["Monto"].sum()
        else:
            total_expenses = 0.0
        
        balance = total_income - total_expenses
        message = (
            f"Este mes tuvimos:\n"
            f"Ingresos totales: ${total_income:.2f}\n"
            f"Gastos totales: ${total_expenses:.2f}\n"
            f"Balance: ${balance:.2f}"
        )
        return message
    except Exception as e:
        return f"Error generando reporte: {str(e)}"
