"""
database.py
-----------
Centralises every interaction with SQLite.
No other module imports sqlite3 directly.

Usage pattern (per-request via Flask g):
    from database import get_db, init_db, close_db
    Before every request  → get_db()  (opens connection, stored on g)
    Teardown every request → close_db()
    App startup            → init_db()
"""

import sqlite3
import os
from datetime import datetime, timezone

from flask import g


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# bank.db lives next to this file in BACKEND/
_DB_PATH = os.path.join(os.path.dirname(__file__), "bank.db")


def _get_db_path() -> str:
    """Return the database file path.  Overridable in tests via app config."""
    return getattr(g, "_db_path", _DB_PATH)


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """
    Open (or return the already-open) per-request database connection.
    Rows are returned as sqlite3.Row objects so columns are accessible by name.
    The connection is stored on Flask's application-context g object.
    """
    if "db" not in g:
        g.db = sqlite3.connect(
            _get_db_path(),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        g.db.row_factory = sqlite3.Row
        # Enforce foreign-key constraints on every connection
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None) -> None:
    """
    Close the per-request database connection (called in teardown_request).
    Skips closing if the connection was injected by the test suite — the test
    fixture owns the connection lifetime and will close it after the test.
    """
    # Import lazily to avoid a hard dependency on the test module at runtime
    try:
        from conftest import _test_db_local  # type: ignore[import]
        if getattr(_test_db_local, "conn", None) is not None:
            # Test connection — just remove it from g; do NOT close it
            g.pop("db", None)
            return
    except ImportError:
        pass

    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """
    Create all tables if they do not already exist.
    Safe to call on every app start — uses CREATE TABLE IF NOT EXISTS.
    """
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            full_name     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL UNIQUE,
            balance     REAL    NOT NULL DEFAULT 0.0,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id       INTEGER NOT NULL,
            transaction_type TEXT    NOT NULL CHECK(transaction_type IN ('deposit','withdrawal')),
            amount           REAL    NOT NULL,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );
    """)
    db.commit()


# ---------------------------------------------------------------------------
# Customer queries
# ---------------------------------------------------------------------------

def get_customer_by_username(username: str):
    """
    Return the customer row matching *username*, or None if not found.
    The row is a sqlite3.Row (accessible by column name).
    """
    db = get_db()
    return db.execute(
        "SELECT id, username, password_hash, full_name FROM customers WHERE username = ?",
        (username,),
    ).fetchone()


def get_customer_by_id(customer_id: int):
    """Return the customer row for *customer_id*, or None."""
    db = get_db()
    return db.execute(
        "SELECT id, username, password_hash, full_name FROM customers WHERE id = ?",
        (customer_id,),
    ).fetchone()


# ---------------------------------------------------------------------------
# Account queries
# ---------------------------------------------------------------------------

def get_account_by_customer_id(customer_id: int):
    """Return the account row for *customer_id*, or None."""
    db = get_db()
    return db.execute(
        "SELECT id, customer_id, balance FROM accounts WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()


def update_account_balance(account_id: int, new_balance: float) -> None:
    """Overwrite the balance for *account_id* with *new_balance*."""
    db = get_db()
    db.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?",
        (new_balance, account_id),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Transaction queries
# ---------------------------------------------------------------------------

def insert_transaction(
    account_id: int,
    transaction_type: str,
    amount: float,
) -> None:
    """
    Record a completed deposit or withdrawal.
    *transaction_type* must be 'deposit' or 'withdrawal'.
    """
    db = get_db()
    db.execute(
        """
        INSERT INTO transactions (account_id, transaction_type, amount, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (account_id, transaction_type, amount, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()


def get_recent_transactions(account_id: int, limit: int = 5):
    """
    Return up to *limit* most-recent transactions for *account_id*,
    newest first.
    """
    db = get_db()
    return db.execute(
        """
        SELECT id, account_id, transaction_type, amount, created_at
        FROM   transactions
        WHERE  account_id = ?
        ORDER  BY id DESC
        LIMIT  ?
        """,
        (account_id, limit),
    ).fetchall()
