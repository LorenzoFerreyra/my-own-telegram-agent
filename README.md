# Telegram Finance Agent

AI-powered Telegram bot that tracks expenses and income to Google Sheets using natural language.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
HTTP_TELEGRAM_TOKEN=your_telegram_bot_token
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_APPLICATION_CREDENTIALS=automatizacion-activos.json
OPENAI_API_KEY=your_openai_api_key
```

3. Share your Google Sheet with the service account email from your credentials file.

## Run Locally

Start the server:
```bash
uvicorn main:app --reload
```

Server runs at: http://127.0.0.1:8000

## Test Locally

Send POST request to `http://127.0.0.1:8000/webhook`:

```json
{
  "message": {
    "chat": {"id": 123456},
    "text": "Gaste 50 dolares en comida"
  }
}
```

## Deploy to AWS Lambda

The application is Lambda-ready using Mangum handler. Package and deploy using your preferred method (SAM, Serverless, etc.).

## Project Structure

- `main.py` - FastAPI server and webhook endpoint
- `agent.py` - LangGraph agent logic
- `tools.py` - Google Sheets integration tools
- `models.py` - Pydantic models
- `config.py` - Auto-generated enum values

## Notes

- The agent uses GPT-4o-mini for natural language understanding
- Categories and payment methods are validated against your Google Sheets

