"""Round-trip tests for the sqlite layer used by the Telegram bot."""

from langchain_core.messages import AIMessage, HumanMessage

from database import (
    is_duplicate,
    load_history,
    mark_processed,
    save_message,
)


def test_init_db_creates_tables(db):
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"updates", "conversations"}.issubset(tables)


def test_is_duplicate_false_before_marking(db):
    assert is_duplicate(db, 42) is False


def test_mark_processed_makes_is_duplicate_true(db):
    mark_processed(db, 42)
    assert is_duplicate(db, 42) is True


def test_mark_processed_is_idempotent(db):
    mark_processed(db, 42)
    mark_processed(db, 42)  # would raise if not INSERT OR IGNORE
    count = db.execute(
        "SELECT COUNT(*) FROM updates WHERE update_id = 42"
    ).fetchone()[0]
    assert count == 1


def test_save_and_load_history_roundtrip(db):
    chat_id = 1001
    save_message(db, chat_id, "human", "hola")
    save_message(db, chat_id, "ai", "hola, ¿en qué puedo ayudarte?")

    history = load_history(db, chat_id)

    assert len(history) == 2
    assert isinstance(history[0], HumanMessage)
    assert history[0].content == "hola"
    assert isinstance(history[1], AIMessage)
    assert history[1].content == "hola, ¿en qué puedo ayudarte?"


def test_load_history_returns_oldest_first(db):
    chat_id = 1002
    for i in range(5):
        save_message(db, chat_id, "human", f"msg-{i}")

    history = load_history(db, chat_id)
    assert [m.content for m in history] == [f"msg-{i}" for i in range(5)]


def test_load_history_respects_limit_and_keeps_most_recent(db):
    chat_id = 1003
    for i in range(10):
        save_message(db, chat_id, "human", f"msg-{i}")

    history = load_history(db, chat_id, limit=3)
    # last 3 inserted, still in chronological order
    assert [m.content for m in history] == ["msg-7", "msg-8", "msg-9"]


def test_load_history_isolates_chats(db):
    save_message(db, 1, "human", "chat one")
    save_message(db, 2, "human", "chat two")

    assert [m.content for m in load_history(db, 1)] == ["chat one"]
    assert [m.content for m in load_history(db, 2)] == ["chat two"]


def test_load_history_ignores_unknown_role(db):
    chat_id = 1004
    save_message(db, chat_id, "human", "kept")
    # bypass save_message to inject a role load_history should skip
    db.execute(
        "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, "system", "should be skipped"),
    )
    db.commit()

    history = load_history(db, chat_id)
    assert [m.content for m in history] == ["kept"]
