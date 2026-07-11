"""
seed.py
-------
One-time script to populate bank.db with demo customers and accounts.
Run directly:  python seed.py

Safe to run multiple times — checks for existing records before inserting.
Prints the demo credentials to the terminal for reference.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

_DB_PATH = os.path.join(os.path.dirname(__file__), "bank.db")

DEMO_CUSTOMERS = [
    {
        "username": "alice",
        "password": "alice123",
        "full_name": "Alice Johnson",
        "opening_balance": 5000.00,
    },
    {
        "username": "bob",
        "password": "bob456",
        "full_name": "Bob Williams",
        "opening_balance": 2500.00,
    },
    {
        "username": "carol",
        "password": "carol789",
        "full_name": "Carol Davis",
        "opening_balance": 10000.00,
    },
]


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they have not been created by the app yet."""
    conn.executescript("""
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
            transaction_type TEXT    NOT NULL,
            amount           REAL    NOT NULL,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );
    """)
    conn.commit()


def seed() -> None:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_tables(conn)

    print("\n=== Banking App — Demo Account Seeder ===\n")

    for demo in DEMO_CUSTOMERS:
        # Check whether this username already exists
        existing = conn.execute(
            "SELECT id FROM customers WHERE username = ?", (demo["username"],)
        ).fetchone()

        if existing:
            print(f"  [SKIP]   {demo['username']} — already exists.")
            continue

        # Insert customer
        cursor = conn.execute(
            "INSERT INTO customers (username, password_hash, full_name) VALUES (?, ?, ?)",
            (
                demo["username"],
                generate_password_hash(demo["password"]),
                demo["full_name"],
            ),
        )
        customer_id = cursor.lastrowid

        # Insert account with opening balance
        conn.execute(
            "INSERT INTO accounts (customer_id, balance) VALUES (?, ?)",
            (customer_id, demo["opening_balance"]),
        )
        conn.commit()

        print(
            f"  [ADDED]  {demo['full_name']:<18} "
            f"username={demo['username']:<8} "
            f"password={demo['password']:<10} "
            f"balance=£{demo['opening_balance']:,.2f}"
        )

    print("\nSeeding complete.  Use the credentials above to log in.\n")
    conn.close()


if __name__ == "__main__":
    seed()
