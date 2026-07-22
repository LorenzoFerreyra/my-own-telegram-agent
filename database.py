import json
import sqlite3

from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

DB_PATH = "processed_updates.db"


def init_db() -> sqlite3.Connection:
    """Create the DB and tables if they don't exist, return connection."""
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS updates (update_id INTEGER PRIMARY KEY)")
    con.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id   INTEGER NOT NULL,
            role      TEXT NOT NULL,
            content   TEXT NOT NULL,
            timestamp DATETIME DEFAULT (datetime('now', '-3 hours'))
        )
    """)
    con.commit()
    return con


# ── deduplication ────────────────────────────────────────────────

def is_duplicate(con: sqlite3.Connection, update_id: int) -> bool:
    """Return True if this update_id was already processed."""
    row = con.execute("SELECT 1 FROM updates WHERE update_id = ?", (update_id,)).fetchone()
    return row is not None


def mark_processed(con: sqlite3.Connection, update_id: int) -> None:
    """Record update_id as successfully processed."""
    con.execute("INSERT OR IGNORE INTO updates (update_id) VALUES (?)", (update_id,))
    con.commit()


# ── conversation history ─────────────────────────────────────────

def save_message(con: sqlite3.Connection, chat_id: int, message: BaseMessage) -> None:
    """Persist a single LangChain message (including tool calls / tool results)."""
    con.execute(
        "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, message.type, json.dumps(message_to_dict(message), ensure_ascii=False))
    )
    con.commit()


def load_history(con: sqlite3.Connection, chat_id: int, limit: int = 20) -> list[BaseMessage]:
    """Load recent conversation history for a chat_id as LangChain messages.

    Only JSON-serialized rows are replayed. Legacy plain-text rows are skipped
    on purpose: they contain AI confirmations with no visible tool call, and
    replaying that pattern teaches the model to confirm transactions without
    actually calling the tools.
    """
    rows = con.execute(
        "SELECT role, content FROM conversations WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (chat_id, limit)
    ).fetchall()
    rows.reverse()
    messages = []
    for _role, content in rows:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue  # legacy plain-text row
        if isinstance(data, dict) and "type" in data and "data" in data:
            messages.extend(messages_from_dict([data]))
    # If the LIMIT window cut a tool sequence in half, drop orphaned tool
    # results so the model never sees a tool message without its tool call.
    while messages and messages[0].type == "tool":
        messages.pop(0)
    return messages
