"""
app.py
------
Flask application entry point.

Responsibilities:
  - Create and configure the Flask app instance.
  - Register per-request database lifecycle hooks.
  - Define all URL routes (thin controllers — delegate to service modules).
  - Register custom error handlers.
  - Bootstrap the database tables and start the dev server.

Run:
    python app.py
"""

import os
from datetime import timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

# Tell Flask where to find templates and static files (in FRONTEND/)
_BASE_DIR = os.path.dirname(__file__)
_FRONTEND_DIR = os.path.join(_BASE_DIR, "..", "FRONTEND")

app = Flask(
    __name__,
    template_folder=os.path.join(_FRONTEND_DIR, "templates"),
    static_folder=os.path.join(_FRONTEND_DIR, "static"),
)

# Secret key — read from environment variable; fall back to dev key if absent.
# IMPORTANT: always set SECRET_KEY via environment variable in production.
app.secret_key = os.environ.get("SECRET_KEY", "dev-banking-secret-key-change-in-prod")

# Sessions expire after 30 minutes of inactivity
app.permanent_session_lifetime = timedelta(minutes=30)


# ---------------------------------------------------------------------------
# Database lifecycle hooks
# ---------------------------------------------------------------------------

from database import get_db, close_db, init_db  # noqa: E402  (after app creation)


@app.before_request
def open_db_connection():
    """Ensure a database connection is available for every request."""
    get_db()


@app.teardown_request
def close_db_connection(exception=None):
    """Close the database connection at the end of every request."""
    close_db(exception)


# ---------------------------------------------------------------------------
# Service imports (after app is created so Flask context is available)
# ---------------------------------------------------------------------------

from auth import (  # noqa: E402
    login_customer,
    create_session,
    logout_customer,
    login_required,
    get_current_customer_id,
    get_current_full_name,
)
from transactions import process_deposit, process_withdrawal  # noqa: E402
from database import get_account_by_customer_id, get_recent_transactions  # noqa: E402


# ---------------------------------------------------------------------------
# Routes — Authentication
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Root URL: redirect to dashboard if logged in, otherwise to login."""
    if get_current_customer_id():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  → render the login form.
    POST → validate credentials; create session on success; show error on failure.
    """
    # Already authenticated — send straight to the dashboard
    if get_current_customer_id():
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        result = login_customer(username, password)

        if result.success:
            create_session(result.data)
            flash(f"Welcome back, {result.data['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            error = result.message

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    """Destroy the session and redirect to login."""
    logout_customer()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """
    Display the customer's name, current balance, and recent transactions.
    """
    customer_id = get_current_customer_id()
    account = get_account_by_customer_id(customer_id)

    if account is None:
        flash("Account not found. Please contact support.", "danger")
        return redirect(url_for("login"))

    recent_txns = get_recent_transactions(account["id"], limit=5)

    return render_template(
        "dashboard.html",
        full_name=get_current_full_name(),
        balance=account["balance"],
        recent_txns=recent_txns,
    )


# ---------------------------------------------------------------------------
# Routes — Deposit
# ---------------------------------------------------------------------------

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """
    GET  → render the deposit form.
    POST → process the deposit; redirect to dashboard on success.
    """
    error = None

    if request.method == "POST":
        raw_amount = request.form.get("amount", "")
        customer_id = get_current_customer_id()

        result = process_deposit(customer_id, raw_amount)

        if result.success:
            flash(result.message, "success")
            return redirect(url_for("dashboard"))
        else:
            error = result.message

    return render_template("deposit.html", error=error)


# ---------------------------------------------------------------------------
# Routes — Withdrawal
# ---------------------------------------------------------------------------

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    """
    GET  → render the withdrawal form with current balance.
    POST → process the withdrawal; redirect to dashboard on success.
    """
    customer_id = get_current_customer_id()
    account = get_account_by_customer_id(customer_id)

    if account is None:
        flash("Account not found. Please contact support.", "danger")
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        raw_amount = request.form.get("amount", "")
        result = process_withdrawal(customer_id, raw_amount)

        if result.success:
            flash(result.message, "success")
            return redirect(url_for("dashboard"))
        else:
            error = result.message

    return render_template(
        "withdraw.html",
        balance=account["balance"],
        error=error,
    )


# ---------------------------------------------------------------------------
# Custom error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Initialise tables (safe to run every time — uses CREATE IF NOT EXISTS)
    with app.app_context():
        init_db()

    print("\n  Banking App is running.")
    print("  Open http://127.0.0.1:5000 in your browser.\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
