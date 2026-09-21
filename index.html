"""
db.py
Handles the play-money ledger using SQLite.
Every balance change is written here so it survives server restarts.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "crash_game.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            session_id TEXT PRIMARY KEY,
            name TEXT,
            balance INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            change_amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            round_nonce INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def create_player(session_id, name, starting_balance):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO players (session_id, name, balance) VALUES (?, ?, ?)",
        (session_id, name, starting_balance)
    )
    conn.commit()
    conn.close()

def get_player(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM players WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def change_balance(session_id, delta, reason, round_nonce=None):
    """Apply a balance change AND log it, in one atomic transaction.
    This is the key idea of a ledger: never just overwrite a balance,
    always record why it changed, so you can audit every credit later."""
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        row = conn.execute("SELECT balance FROM players WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise ValueError("Player not found")
        new_balance = row["balance"] + delta
        if new_balance < 0:
            raise ValueError("Insufficient balance")
        conn.execute("UPDATE players SET balance = ? WHERE session_id = ?", (new_balance, session_id))
        conn.execute(
            "INSERT INTO ledger (session_id, change_amount, reason, round_nonce) VALUES (?, ?, ?, ?)",
            (session_id, delta, reason, round_nonce)
        )
        conn.commit()
        return new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
