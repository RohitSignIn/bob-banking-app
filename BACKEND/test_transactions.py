"""
test_transactions.py
--------------------
Unit tests for transactions.py service functions.

Uses an in-memory SQLite database populated with a seeded customer and account.
All tests run within a Flask app context because database.py uses Flask's g.
"""

import sqlite3
import pytest
from werkzeug.security import generate_password_hash


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    from app import app as flask_app
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret-key")
    return flask_app


@pytest.fixture()
def seeded_account(app):
    """
    Provides a live in-memory database with one customer whose balance is 500.00.
    Returns the account id so tests can query the balance directly.
    """
    from flask import g

    with app.app_context():
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL
            );
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE,
                balance REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );
        """)
        conn.execute(
            "INSERT INTO customers (username, password_hash, full_name) VALUES (?,?,?)",
            ("testuser", generate_password_hash("pass"), "Test User"),
        )
        cust = conn.execute("SELECT id FROM customers WHERE username='testuser'").fetchone()
        conn.execute(
            "INSERT INTO accounts (customer_id, balance) VALUES (?,?)",
            (cust["id"], 500.00),
        )
        conn.commit()

        g.db = conn
        g._db_path = ":memory:"

        account = conn.execute(
            "SELECT * FROM accounts WHERE customer_id=?", (cust["id"],)
        ).fetchone()

        yield {"conn": conn, "customer_id": cust["id"], "account_id": account["id"]}


def _get_balance(conn, account_id):
    return conn.execute(
        "SELECT balance FROM accounts WHERE id=?", (account_id,)
    ).fetchone()["balance"]


def _txn_count(conn, account_id):
    return conn.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE account_id=?", (account_id,)
    ).fetchone()["cnt"]


# ── Deposit tests ────────────────────────────────────────────────────────────

class TestDeposit:

    def test_valid_deposit_increases_balance(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "200")
        assert result.success is True
        balance = _get_balance(seeded_account["conn"], seeded_account["account_id"])
        assert balance == pytest.approx(700.00)

    def test_deposit_records_transaction(self, app, seeded_account):
        from transactions import process_deposit
        process_deposit(seeded_account["customer_id"], "100")
        assert _txn_count(seeded_account["conn"], seeded_account["account_id"]) == 1

    def test_deposit_zero_fails(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "0")
        assert result.success is False
        assert "greater than zero" in result.message.lower()

    def test_deposit_negative_fails(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "-50")
        assert result.success is False

    def test_deposit_non_numeric_fails(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "abc")
        assert result.success is False
        assert "number" in result.message.lower()

    def test_deposit_empty_string_fails(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "")
        assert result.success is False

    def test_deposit_exceeds_maximum_fails(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "2000000")
        assert result.success is False
        assert "maximum" in result.message.lower()

    def test_deposit_decimal_amount(self, app, seeded_account):
        from transactions import process_deposit
        result = process_deposit(seeded_account["customer_id"], "99.99")
        assert result.success is True
        balance = _get_balance(seeded_account["conn"], seeded_account["account_id"])
        assert balance == pytest.approx(599.99)


# ── Withdrawal tests ─────────────────────────────────────────────────────────

class TestWithdrawal:

    def test_valid_withdrawal_decreases_balance(self, app, seeded_account):
        from transactions import process_withdrawal
        result = process_withdrawal(seeded_account["customer_id"], "100")
        assert result.success is True
        balance = _get_balance(seeded_account["conn"], seeded_account["account_id"])
        assert balance == pytest.approx(400.00)

    def test_withdrawal_records_transaction(self, app, seeded_account):
        from transactions import process_withdrawal
        process_withdrawal(seeded_account["customer_id"], "50")
        assert _txn_count(seeded_account["conn"], seeded_account["account_id"]) == 1

    def test_withdrawal_exact_balance_succeeds(self, app, seeded_account):
        from transactions import process_withdrawal
        result = process_withdrawal(seeded_account["customer_id"], "500")
        assert result.success is True
        balance = _get_balance(seeded_account["conn"], seeded_account["account_id"])
        assert balance == pytest.approx(0.00)

    def test_withdrawal_exceeds_balance_fails(self, app, seeded_account):
        from transactions import process_withdrawal
        result = process_withdrawal(seeded_account["customer_id"], "600")
        assert result.success is False
        assert "insufficient" in result.message.lower()

    def test_withdrawal_zero_fails(self, app, seeded_account):
        from transactions import process_withdrawal
        result = process_withdrawal(seeded_account["customer_id"], "0")
        assert result.success is False

    def test_withdrawal_negative_fails(self, app, seeded_account):
        from transactions import process_withdrawal
        result = process_withdrawal(seeded_account["customer_id"], "-100")
        assert result.success is False

    def test_withdrawal_non_numeric_fails(self, app, seeded_account):
        from transactions import process_withdrawal
        result = process_withdrawal(seeded_account["customer_id"], "fifty")
        assert result.success is False

    def test_balance_unchanged_after_failed_withdrawal(self, app, seeded_account):
        from transactions import process_withdrawal
        process_withdrawal(seeded_account["customer_id"], "9999")
        balance = _get_balance(seeded_account["conn"], seeded_account["account_id"])
        assert balance == pytest.approx(500.00)
