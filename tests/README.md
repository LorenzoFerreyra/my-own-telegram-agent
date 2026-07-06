# Local test suite

Runs on demand — not wired into any CI.

## Setup (one time)

```powershell
pip install -r requirements-dev.txt
```

## Run

From the project root:

```powershell
pytest -q
```

Or a single file:

```powershell
pytest tests/test_database.py -q
```

## What is / isn't covered

Covered — deterministic, no network:
- `database.py`: dedup + conversation history round-trips
- `tools.py::_fuzzy_match` and the invalid-category / invalid-payment branches of `add_expense` / `add_income`
- `agent.py::should_continue` routing

Not covered on purpose — would need mocking that costs more than the tests give:
- Real gspread writes and monthly-report aggregation
- Ollama calls (`call_model`)
- Telegram polling / `handle_message`
