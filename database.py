import sqlite3

DB_PATH = "processed_updates.db"


def init_db() -> sqlite3.Connection:
    """Create the DB and table if they don't exist, return connection."""
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS updates (update_id INTEGER PRIMARY KEY)")
    con.commit()
    return con


def is_duplicate(con: sqlite3.Connection, update_id: int) -> bool:
    """Return True if this update_id was already processed."""
    row = con.execute("SELECT 1 FROM updates WHERE update_id = ?", (update_id,)).fetchone()
    return row is not None


def mark_processed(con: sqlite3.Connection, update_id: int) -> None:
    """Record update_id as successfully processed."""
    con.execute("INSERT OR IGNORE INTO updates (update_id) VALUES (?)", (update_id,))
    con.commit()
