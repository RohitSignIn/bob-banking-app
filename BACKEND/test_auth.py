"""
test_auth.py
------------
Unit tests for auth.py service functions.

Uses an in-memory SQLite database so tests are fast and isolated.
The Flask app context is required because database.py reads from Flask's g.
"""

import pytest
import sqlite3
from werkzeug.security import generate_password_hash

# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    """Create a fully configured Flask test app."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    from app import app as flask_app
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret-key")
    return flask_app


@pytest.fixture()
def in_memory_db(app):
    """
    Push an app context with an in-memory SQLite connection on g,
    create tables, and insert one demo customer.
    Yields the connection so tests can query it directly if needed.
    """
    from flask import g

    with app.app_context():
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        # Create tables
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

        # Seed one customer
        conn.execute(
            "INSERT INTO customers (username, password_hash, full_name) VALUES (?,?,?)",
            ("alice", generate_password_hash("alice123"), "Alice Johnson"),
        )
        cust_id = conn.execute("SELECT id FROM customers WHERE username='alice'").fetchone()["id"]
        conn.execute(
            "INSERT INTO accounts (customer_id, balance) VALUES (?,?)",
            (cust_id, 1000.00),
        )
        conn.commit()

        # Attach the connection to Flask g so database.py helpers use it
        g.db = conn
        g._db_path = ":memory:"

        yield conn


# ── Tests ────────────────────────────────────────────────────────────────────

class TestLoginCustomer:

    def test_login_succeeds_with_correct_credentials(self, app, in_memory_db):
        from auth import login_customer
        result = login_customer("alice", "alice123")
        assert result.success is True
        assert result.data is not None
        assert result.data["username"] == "alice"

    def test_login_fails_with_wrong_password(self, app, in_memory_db):
        from auth import login_customer
        result = login_customer("alice", "wrongpassword")
        assert result.success is False
        assert "Invalid" in result.message

    def test_login_fails_with_unknown_username(self, app, in_memory_db):
        from auth import login_customer
        result = login_customer("nobody", "anything")
        assert result.success is False
        assert "Invalid" in result.message

    def test_login_fails_with_blank_username(self, app, in_memory_db):
        from auth import login_customer
        result = login_customer("", "alice123")
        assert result.success is False
        assert "required" in result.message.lower()

    def test_login_fails_with_blank_password(self, app, in_memory_db):
        from auth import login_customer
        result = login_customer("alice", "")
        assert result.success is False
        assert "required" in result.message.lower()

    def test_error_message_is_generic_for_bad_username(self, app, in_memory_db):
        """
        The error for wrong username must be identical to wrong password
        to prevent username enumeration attacks.
        """
        from auth import login_customer
        r_bad_user = login_customer("nobody", "anything")
        r_bad_pass = login_customer("alice", "wrongpass")
        assert r_bad_user.message == r_bad_pass.message


class TestSessionHelpers:

    def test_create_session_stores_customer_id(self, app, in_memory_db):
        from auth import create_session, get_current_customer_id
        with app.test_request_context("/"):
            from flask import session as flask_session
            row = in_memory_db.execute("SELECT * FROM customers WHERE username='alice'").fetchone()
            create_session(row)
            assert get_current_customer_id() == row["id"]

    def test_logout_clears_session(self, app, in_memory_db):
        from auth import create_session, logout_customer, get_current_customer_id
        with app.test_request_context("/"):
            row = in_memory_db.execute("SELECT * FROM customers WHERE username='alice'").fetchone()
            create_session(row)
            logout_customer()
            assert get_current_customer_id() is None
