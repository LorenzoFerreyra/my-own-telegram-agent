import sqlite3
import json
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

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
            timestamp DATETIME DEFAULT (datetime('now'))
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

def save_message(con: sqlite3.Connection, chat_id: int, role: str, content: str) -> None:
    """Persist a single message for a chat."""
    con.execute(
        "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content)
    )
    con.commit()


def load_history(con: sqlite3.Connection, chat_id: int) -> list[BaseMessage]:
    """Load full conversation history for a chat_id as LangChain messages."""
    rows = con.execute(
        "SELECT role, content FROM conversations WHERE chat_id = ? ORDER BY id",
        (chat_id,)
    ).fetchall()
    messages = []
    for role, content in rows:
        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
    return messages
