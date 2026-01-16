from fastapi import FastAPI
from models import TelegramMessage
from mangum import Mangum
from agent import build_graph
from langchain_core.messages import HumanMessage
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
agent = build_graph()

async def send_telegram_message(chat_id: int, text: str):
    """Send a message back to Telegram"""
    bot_token = os.getenv("HTTP_TELEGRAM_TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text
        })

@app.get("/")
def read_root():
    return {"status": "ok", "message": "server de finanzas personales está ON"}

@app.post("/webhook")
async def telegram_webhook(update: TelegramMessage):
    
    chat_id = update.message.get("chat", {}).get("id")
    text = update.message.get("text", "")
    
    print(f"Recibido mensaje de {chat_id}: {text}")
    
    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=text)],
            "chat_id": chat_id
        })
        
        last_message = result["messages"][-1]
        response_text = last_message.content
        await send_telegram_message(chat_id, response_text)
        
        print(f"Respuesta enviada: {response_text}")
        
    except Exception as e:
        error_msg = f"Lo siento, ocurrió un error: {str(e)}"
        await send_telegram_message(chat_id, error_msg)
        print(f"Error: {e}")
    
    return {"status": "success"}

handler = Mangum(app)
