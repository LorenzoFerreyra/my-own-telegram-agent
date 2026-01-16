from fastapi import FastAPI, Request
from models import TelegramMessage
from mangum import Mangum
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "server de finanzas personales está ON"}

@app.post("/webhook")
async def telegram_webhook(update: TelegramMessage):

    chat_id = update.message.get("chat", {}).get("id")
    text = update.message.get("text", "")
    

    print(f"Recibido mensaje de {chat_id}: {text}")
    
    return {"status": "success"}

handler = Mangum(app)