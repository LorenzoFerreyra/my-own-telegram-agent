from langchain_core.tools import tool
from models import FinanceEntry
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_gspread_client():
    """Initialize and return a gspread client using service account from environment"""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if creds_file and os.path.exists(creds_file):
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    else:
        print("There is no credentials file, bro")
    
    return gspread.authorize(creds)

@tool
def add_expense(amount: float, description: str, category: str = "general", payment_method: str = "efectivo") -> str:
    """Add an expense (gasto/entrada de material) to the Google Sheet. Use this when the user mentions spending money or an expense.
    
    Args:
        amount: The amount of money spent (positive number)
        description: What the expense was for (goes in Notas field)
        category: Category of the expense (e.g., comida, transporte, entretenimiento, servicios)
        payment_method: Payment method (e.g., efectivo, tarjeta, transferencia)
    
    Returns:
        Confirmation message
    """
    try:
        client = get_gspread_client()
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        

        worksheet = spreadsheet.worksheet("EntradaMaterial")  
        
        
        unique_id = f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Row structure matching AppSheet:
        # EntradaMaterialID, Fecha, Hora, UsuarioID, Status, Monto, Categoria, Notas, MetodoPago
        row = [
            unique_id,
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
        return f"Error al registrar gasto: {str(e)}"

@tool
def add_income(amount: float, description: str, category: str = "general", payment_method: str = "efectivo") -> str:
    """Add income (venta/ingreso) to the Google Sheet. Use this when the user mentions receiving money or income.
    
    Args:
        amount: The amount of money received (positive number)
        description: What the income was for (goes in VentaNotas field)
        category: Category of the income (e.g., salario, freelance, regalo, venta)
        payment_method: Payment method (e.g., efectivo, tarjeta, transferencia)
    
    Returns:
        Confirmation message
    """
    try:
        client = get_gspread_client()
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        
        
        worksheet = spreadsheet.worksheet("Ventas")
        
        
        unique_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        
        row = [
            unique_id,
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
        return f"Error al registrar ingreso: {str(e)}"
