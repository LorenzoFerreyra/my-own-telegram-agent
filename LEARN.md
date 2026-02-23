# Learn: Build a Local-First Telegram Finance Agent

A short, classroom-ready path to teach or learn how this project works. Keep it hands-on and privacy-first.

## Who this is for
- Students who want a practical AI+automation project
- Instructors looking for a 1–3 session lab that fits CS/IT curricula

## Learning goals
- Understand how Telegram bots poll and respond
- Run a small local LLM (Ollama + qwen3:4b) for private inference
- Route user messages through a LangGraph agent and tools
- Persist data to both SQLite and Google Sheets safely

## Module plan (3 x ~60 min)
1) Foundations
   - Clone, create virtualenv, install `requirements.txt`
   - Explain message flow (Telegram -> LangGraph -> Ollama -> Sheets)
   - Explore config and categories in `config.py`
2) Local LLM + Tools
   - Pull model: `ollama pull qwen3:4b`
   - Walk through `agent.py` and `tools.py` to see how intents map to actions
   - Lab: add a new expense category and validate end-to-end
3) Data + Reliability
   - Inspect SQLite creation and dedup logic in `database.py`
   - Wire Google Sheets credentials and practice writing test rows
   - Lab: run `bash start_bot.sh`, force a crash, confirm auto-restart loop

## Hands-on labs (ready-to-run)
- Lab A: Echo-only bot (comment out tool calls) to verify Telegram webhook polling
- Lab B: Add a "monthly summary" tool that reads last 30 days from Sheets and returns totals
- Lab C: Hardening exercise: reject messages from unknown Telegram user IDs
- Lab D: Observability: add structured logs for each tool call and view them via `Get-Content bot_log.txt -Wait`

## Reflection prompts
- What privacy advantages come from local LLM inference vs cloud APIs?
- Where could rate limits or failures occur, and how would you surface them to the user?
- How would you generalize this agent for multiple family members with different categories?

## Stretch ideas
- Swap `qwen3:4b` for a distilled model and compare latency/accuracy
- Add OCR ingestion for receipts (tie into a new tool)
- Build a "budget drift" report that flags overspending categories weekly

## Assessment checklist
- Bot runs locally; responds to at least one expense command
- SQLite file created and dedup prevents double-booking on restart
- Google Sheets receives a test transaction row
- A new category/tool added and handled correctly by the agent

## Teaching tips
- Keep `.env` out of version control; demo why secrets matter
- Use small, iterative changes and rerun often; show how crashes auto-restart
- Pair students: one drives code, the other traces flow against the diagram

## Resources
- Telegram Bot API: https://core.telegram.org/bots/api
- Ollama: https://ollama.com
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Google Sheets API (Python): https://developers.google.com/sheets/api/quickstart/python
