# Telegram Finance Agent

Personal finance assistant that lives in your Telegram. Send a message like _"gasté 10 mil en internet"_ and it classifies, records and confirms the transaction — all processed locally on your machine, no data sent to external AI providers.

## How it works

```
You (Telegram)
      ↓
Bot polls Telegram for new messages
      ↓
LangGraph agent decides what to do
      ↓
qwen3:4b running on Ollama (local GPU)
      ↓
Writes to Google Sheets via gspread
      ↓
Confirms back to Telegram
```

## Privacy

All LLM inference runs on your local machine via **Ollama**. Your financial data never touches OpenAI, Anthropic, or any external AI service.

## Hardware requirements

Tested on:
- CPU: AMD Ryzen 5
- RAM: 32 GB
- GPU: NVIDIA RTX 4060 8GB — model runs fully on GPU

Minimum: any machine with ~3GB VRAM or 8GB RAM for CPU inference.

## Prerequisites

### Ollama
Install Ollama from [https://ollama.com](https://ollama.com) using the official Windows installer.

- The installer registers Ollama as a **Windows background service** that starts automatically at boot
- No need to open the desktop app or run `ollama serve` manually — it's already running
- Verify it's up at any time: `http://localhost:11434` should return `Ollama is running`

```bash
# Pull the model once after installing
ollama pull qwen3:4b
```

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables
Create a `.env` file in the project root:
```env
HTTP_TELEGRAM_TOKEN=your_telegram_bot_token
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
OLLAMA_BASE_URL=http://localhost:11434
```

> `OLLAMA_BASE_URL` defaults to `http://localhost:11434` if omitted.

### 3. Share your Google Sheet
Share the spreadsheet with the service account email from your credentials JSON file (Editor access).

## Run

```bash
python main.py
```

No server, no public URL, no ngrok needed. The bot polls Telegram directly.

### Run with auto-restart (recommended)

Using **Git Bash** (preferred):
```bash
bash start_bot.sh
```

The script loops forever and restarts the bot automatically if it crashes:
```bash
#!/bin/bash
cd "$(dirname "$0")"
while true; do
    .venv/Scripts/python.exe main.py
    echo "Bot crashed, restarting in 5 seconds..."
    sleep 5
done
```

> First time only: `chmod +x start_bot.sh` to make it executable.

### Run on Windows startup (optional)

Run once in PowerShell to register it as a scheduled task at login:

```powershell
$action = New-ScheduledTaskAction `
    -Execute "C:\Users\Lorenzo\Documents\Desktop project versions\my-own-telegram-agent\.venv\Scripts\python.exe" `
    -Argument "start_bot.sh" `
    -WorkingDirectory "C:\Users\Lorenzo\Documents\Desktop project versions\my-own-telegram-agent"

$trigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask -TaskName "TelegramFinanceBot" -Action $action -Trigger $trigger -RunLevel Highest
```

## Project structure

```
├── main.py          # Telegram polling loop and message handler
├── agent.py         # LangGraph agent — calls Ollama, routes to tools
├── tools.py         # Google Sheets read/write tools (add_expense, add_income)
├── database.py      # SQLite helpers — conversation history + dedup
├── models.py        # Pydantic models and AgentState
├── config.py        # Valid categories and payment methods from the sheet
├── start_bot.sh     # Git Bash launcher with auto-restart
└── .env             # Secrets — never commit this
```

## Data persistence

A local `processed_updates.db` SQLite file is created automatically on first run with two tables:

| Table | Purpose |
|-------|---------|
| `updates` | Stores processed `update_id`s to prevent double-booking on crashes |
| `conversations` | Full message history per `chat_id` — survives bot restarts |

## Notes

- Model: `qwen3:4b` — fits in 3GB VRAM, ~500ms response time
- Qwen3 thinking tokens (`<think>...</think>`) are stripped before replying
- Conversation context is loaded from SQLite on every message, so the bot remembers previous turns even after a restart
- Categories and payment methods are validated against the values in `config.py`
- Ollama runs as a Windows background service — no desktop app required