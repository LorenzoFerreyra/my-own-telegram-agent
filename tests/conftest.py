"""Shared fixtures. Isolates every test from the real sqlite file, env, and network."""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

# Make the project root importable (database, tools, ...)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Stop tests from touching the real DB or real Google Sheet."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(tmp_path / "nope.json"))


@pytest.fixture
def db():
    """In-memory sqlite pre-populated with the app's schema."""
    from database import init_db

    # init_db writes to DB_PATH; because we chdir'd to tmp_path it lands there
    con = init_db()
    yield con
    con.close()


@pytest.fixture
def mem_db():
    """Alternative: raw :memory: connection for tests that don't need init_db's schema."""
    con = sqlite3.connect(":memory:")
    yield con
    con.close()
