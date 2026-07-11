"""
conftest.py
-----------
Shared pytest fixtures.

The core problem with testing a module-level Flask singleton is that
`before_request` hooks cannot be added after the first request is handled.

Solution: override the `open_db_connection` hook by storing a per-test
connection in the app config under TEST_DB, then have the open_db_connection
hook in app.py check for it.  This keeps the hook registered at app startup
but lets tests inject a different connection.

Alternatively (and more cleanly), we use a test marker in config so the
existing get_db() function in database.py picks up the test connection.

The approach used here: patch database._get_db_path to point at ':memory:'
is unreliable because each call creates a *new* in-memory DB.

Correct approach: set g.db directly via a wrapper around the test client
open() call using Flask's test request context, or use the DATABASE_URL
config override.  We use the simplest reliable method: override the
`open_db_connection` before_request hook via a subclassed Flask app —
but since we have a module-level singleton that's already registered hooks,
we instead use the `_inject_test_db` function that is registered ONCE at
module import time (before any request) and controlled via a thread-local.
"""

import sqlite3
import threading
import pytest
from werkzeug.security import generate_password_hash

# Thread-local storage so each test's DB connection is isolated
_test_db_local = threading.local()


def _build_in_memory_db() -> sqlite3.Connection:
    """Create and seed a fresh in-memory SQLite database."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE customers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            full_name     TEXT    NOT NULL
        );
        CREATE TABLE accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL UNIQUE,
            balance     REAL    NOT NULL DEFAULT 0.0,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE TABLE transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id       INTEGER NOT NULL,
            transaction_type TEXT    NOT NULL,
            amount           REAL    NOT NULL,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );
    """)
    conn.execute(
        "INSERT INTO customers (username, password_hash, full_name) VALUES (?,?,?)",
        ("alice", generate_password_hash("alice123"), "Alice Johnson"),
    )
    cust_id = conn.execute(
        "SELECT id FROM customers WHERE username='alice'"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO accounts (customer_id, balance) VALUES (?,?)",
        (cust_id, 1000.00),
    )
    conn.commit()
    return conn


def pytest_configure(config):
    """
    Register the test-DB injection hook ONCE at the very start of the test
    session, before any request is ever handled.  We patch database.get_db
    so that when _test_db_local.conn is set, it returns that instead of
    opening the real bank.db file.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    import database

    original_get_db = database.get_db

    def test_aware_get_db():
        from flask import g
        # If a test has set a connection on the thread-local, use it
        test_conn = getattr(_test_db_local, "conn", None)
        if test_conn is not None:
            if "db" not in g:
                g.db = test_conn
            return g.db
        return original_get_db()

    database.get_db = test_aware_get_db


@pytest.fixture()
def client():
    """
    Flask test client backed by a fresh in-memory database for every test.
    Sets _test_db_local.conn before the test and clears it after.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    from app import app as flask_app
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret")

    test_db = _build_in_memory_db()
    _test_db_local.conn = test_db

    with flask_app.test_client() as test_client:
        yield test_client

    _test_db_local.conn = None
    test_db.close()
