"""
auth.py
-------
Authentication service layer.
Handles credential verification, session lifecycle, and the login_required
decorator that protects every restricted route.

Nothing in this file knows about HTML or HTTP methods — it works purely with
data and Flask's session/redirect helpers.
"""

import functools

from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash

from database import get_customer_by_username
from models import TransactionResult


# ---------------------------------------------------------------------------
# Login service
# ---------------------------------------------------------------------------

def login_customer(username: str, password: str) -> TransactionResult:
    """
    Verify *username* and *password* against the database.

    Returns a TransactionResult:
        success=True  → .data holds the customer row
        success=False → .message holds a safe error string

    Security: a single generic error message is returned regardless of
    whether the username or the password is wrong.  This prevents attackers
    from enumerating valid usernames.
    """
    # Guard: reject blank inputs before hitting the database
    if not username or not username.strip():
        return TransactionResult(success=False, message="Username is required.")
    if not password:
        return TransactionResult(success=False, message="Password is required.")

    customer = get_customer_by_username(username.strip())

    if customer is None:
        # Username not found — return generic message
        return TransactionResult(
            success=False, message="Invalid username or password."
        )

    if not check_password_hash(customer["password_hash"], password):
        # Password wrong — same generic message as above
        return TransactionResult(
            success=False, message="Invalid username or password."
        )

    return TransactionResult(success=True, message="Login successful.", data=customer)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(customer_row) -> None:
    """
    Store the minimum necessary identity data in the signed Flask session.
    Never store the password hash or full account data in the session.
    """
    session.clear()                          # wipe any leftover data first
    session["customer_id"] = customer_row["id"]
    session["full_name"] = customer_row["full_name"]
    session["username"] = customer_row["username"]
    session.permanent = True                 # honour PERMANENT_SESSION_LIFETIME


def logout_customer() -> None:
    """Destroy the current session completely."""
    session.clear()


def get_current_customer_id() -> int | None:
    """Return the logged-in customer's ID, or None if not authenticated."""
    return session.get("customer_id")


def get_current_full_name() -> str | None:
    """Return the logged-in customer's display name, or None."""
    return session.get("full_name")


# ---------------------------------------------------------------------------
# Route protection decorator
# ---------------------------------------------------------------------------

def login_required(view_func):
    """
    Decorator that protects a Flask route.

    Usage:
        @app.route("/dashboard")
        @login_required
        def dashboard():
            ...

    If no valid session exists the visitor is redirected to /login.
    The decorator preserves the original function name so Flask's
    url_for() keeps working correctly.
    """
    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        if get_current_customer_id() is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped
