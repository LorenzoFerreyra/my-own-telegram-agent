from langchain_core.tools import tool
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
from dotenv import load_dotenv
import uuid
from config import ENTRADA_CATEGORIES, ENTRADA_PAYMENT_METHODS, VENTAS_CATEGORIES, VENTAS_PAYMENT_METHODS

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
    
    # Validate
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
        return f"Gasto registrado: ${amount} en {description} ({category})"
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
        return f"Ingreso registrado: ${amount} de {description} ({category})"
    except Exception as e:
        return f"Error: {str(e)}"
