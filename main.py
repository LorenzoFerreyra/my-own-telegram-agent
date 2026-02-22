from collections import defaultdict
from telegram.ext import Application, MessageHandler, filters
from agent import build_graph
from langchain_core.messages import HumanMessage, AIMessage
from database import init_db, is_duplicate, mark_processed
import os
from dotenv import load_dotenv

load_dotenv()

agent = build_graph()

# In-memory conversation history per chat_id (resets on restart)
conversation_history = defaultdict(list)
# sqlite initialization for deduplication
db = init_db()


async def handle_message(update, context):
    update_id = update.update_id
    chat_id = update.message.chat_id
    text = update.message.text

    if is_duplicate(db, update_id):
        print(f"Skipping duplicate update_id: {update_id}")
        return

    print(f"Recibido mensaje de {chat_id}: {text}")

    conversation_history[chat_id].append(HumanMessage(content=text))

    try:
        result = agent.invoke({
            "messages": conversation_history[chat_id],
            "chat_id": chat_id
        })

        last_message = result["messages"][-1]
        response_text = last_message.content

        conversation_history[chat_id].append(AIMessage(content=response_text))

        await context.bot.send_message(chat_id=chat_id, text=response_text)
        mark_processed(db, update_id)
        print(f"Respuesta enviada: {response_text}")

    except Exception as e:
        error_msg = f"Lo siento, ocurrió un error: {str(e)}"
        await context.bot.send_message(chat_id=chat_id, text=error_msg)
        print(f"Error: {e}")


def main():
    token = os.getenv("HTTP_TELEGRAM_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot polling started... (CTRL+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()

