# Telegram Finance Agent

Personal finance assistant that lives in your Telegram. Send a message like _"gasté 10 mil en internet"_ and it classifies, records and confirms the transaction, all processed locally on your machine, no data sent to external AI providers.

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
- GPU: NVIDIA RTX 4060 8GB  model runs fully on GPU

Minimum: any machine with ~3GB VRAM or 8GB RAM for CPU inference.

## Prerequisites

### Ollama
Install Ollama from [https://ollama.com](https://ollama.com) using the official Windows installer.

- The installer registers Ollama as a **Windows background service** that starts automatically at boot
- No need to open the desktop app or run `ollama serve` manually  it's already running
- Verify it's up at any time: `http://localhost:11434` should return `Ollama is running`

```bash

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

### Option B: Headless Windows launcher (no terminal window)

If you don't want any terminal window showing up at all, use `start_bot.vbs` instead.
It launches Ollama and the bot completely silently, and auto-restarts on crash.

**How it works:**
1. Starts `ollama serve` hidden in the background
2. Waits 3 seconds for Ollama to be ready
3. Runs the bot in a loop  no visible window, logs go to `bot_log.txt`

**Usage:** just double-click `start_bot.vbs`, or register it as a scheduled task (see below).

> To monitor the bot while headless: `Get-Content bot_log.txt -Wait` in PowerShell.

### Run on Windows startup (optional)

**Option A  Shell script via scheduled task:**

```powershell
$action = New-ScheduledTaskAction `
    -Execute "C:\Users\Lorenzo\Documents\Desktop project versions\my-own-telegram-agent\.venv\Scripts\python.exe" `
    -Argument "start_bot.sh" `
    -WorkingDirectory "C:\Users\Lorenzo\Documents\Desktop project versions\my-own-telegram-agent"

$trigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask -TaskName "TelegramFinanceBot" -Action $action -Trigger $trigger -RunLevel Highest
```

**Option B  VBS launcher (fully headless, recommended for Windows):**

Run once in **admin** PowerShell  starts at login, no windows ever:

```powershell
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"C:\Users\Lorenzo\Documents\Desktop project versions\my-own-telegram-agent\start_bot.vbs`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "TelegramBot" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
```

Start it immediately without rebooting:
```powershell
Start-ScheduledTask -TaskName "TelegramBot"
```

Stop or remove it:
```powershell
Stop-ScheduledTask -TaskName "TelegramBot"
Unregister-ScheduledTask -TaskName "TelegramBot" -Confirm:$false
```

## Project structure

```
├── main.py          # Telegram polling loop and message handler
├── agent.py         # LangGraph agent  calls Ollama, routes to tools
├── tools.py         # Google Sheets read/write tools (add_expense, add_income)
├── database.py      # SQLite helpers  conversation history + dedup
├── models.py        # Pydantic models and AgentState
├── config.py        # Valid categories and payment methods from the sheet
├── start_bot.sh     # Git Bash launcher with auto-restart
├── start_bot.vbs    # Headless Windows launcher  no terminal window, auto-restarts
└── .env             # Secrets  never commit this
```

## Data persistence

A local `processed_updates.db` SQLite file is created automatically on first run with two tables:

| Table | Purpose |
|-------|---------|
| `updates` | Stores processed `update_id`s to prevent double-booking on crashes |
| `conversations` | Full message history per `chat_id`  survives bot restarts |

## Notes

- Model: `qwen3:4b`  fits in 3GB VRAM, ~500ms response time
- Qwen3 thinking tokens (`<think>...</think>`) are stripped before replying
- Conversation context is loaded from SQLite on every message, so the bot remembers previous turns even after a restart
- Categories and payment methods are validated against the values in `config.py`
- Ollama runs as a Windows background service. no desktop app required

## TODO

- Add Telegram user authentication (currently open to all)
- Add OCR ingestion for PDF and image invoices
- Keep a coherent conversation chain across turns
- Fix the monthly balance quick-report tool
- Improve logging quality and structure
- Build more financial analysis tools
- Support multi-tenant use so other family members can use the bot (currently IDs are hardcoded)