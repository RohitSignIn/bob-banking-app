# Banking Web Application — Step-by-Step Implementation Guide

> **Document type:** Plain-English instructions and logic.
> This guide explains **what to do and why** at every step.
> It does not contain complete source code, SQL scripts, or API contracts.
> Read [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for architecture context before starting.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### 1.1 Prerequisites

Before writing a single line of code, confirm the following tools are installed on your machine:

- **Python 3.8 or higher** — the runtime for Flask.
- **pip** — Python's package manager, used to install Flask and its dependencies.
- **A terminal / command prompt** — PowerShell on Windows, Terminal on macOS/Linux.
- **A code editor** — VS Code is recommended.

To verify Python is available, open a terminal and type `python --version`. You should see a version number. If not, download Python from python.org and install it before continuing.

---

### 1.2 Create the Project Folder Structure

Create two top-level folders at the root of the project:

- `FRONTEND/` — will hold all HTML templates and static assets (CSS, JS).
- `BACKEND/` — will hold all Python files, the database, and the requirements file.

Inside `FRONTEND/`, create two sub-folders:
- `templates/` — where Flask will look for HTML files to render.
- `static/css/` and `static/js/` — for any custom stylesheet or script files.

Inside `BACKEND/`, you will later create individual Python files for each concern (app, auth, database, etc.). For now, just ensure the folder exists.

This separation enforces the principle that frontend (presentation) and backend (logic) concerns never mix into the same location.

---

### 1.3 Create and Activate a Virtual Environment

A virtual environment is an isolated Python installation specific to this project. It prevents your project's dependencies from conflicting with other Python projects on the same machine.

**Steps:**

1. Open a terminal and navigate to the `BACKEND/` folder.
2. Run the command to create a virtual environment. Python's built-in `venv` module handles this — no extra tool is needed.
3. Once created, activate the virtual environment. The activation command differs by operating system:
   - On **Windows** (PowerShell): run the `Activate.ps1` script inside the `venv/Scripts/` folder.
   - On **macOS / Linux**: source the `activate` script inside `venv/bin/`.
4. After activation, your terminal prompt will show the name of the virtual environment in parentheses. This confirms all subsequent `pip install` commands will install into this isolated environment, not the global Python installation.

> Always activate the virtual environment before running the Flask app or installing packages.

---

### 1.4 Create and Populate `requirements.txt`

The `requirements.txt` file lists every Python package this project depends on. Storing it in `BACKEND/` lets anyone reproduce your environment with a single command.

The minimum packages needed are:

| Package | Purpose |
|---|---|
| `Flask` | The web framework — handles routing, templates, and sessions. |
| `Werkzeug` | Ships with Flask; provides the password hashing utilities you will use. |

Simply list these package names (with optional pinned version numbers) in `requirements.txt`, one per line.

---

### 1.5 Install Dependencies

With the virtual environment active, run `pip install -r requirements.txt` from inside `BACKEND/`. pip will download and install Flask and Werkzeug (and their own dependencies) into the virtual environment.

After installation, run `pip list` to confirm the packages are present.

---

### 1.6 Verify Flask is Working

Create a minimal `app.py` file inside `BACKEND/` with a single route that returns the text "Hello, Banking App". Run the file with `python app.py`. Open a browser and navigate to `http://127.0.0.1:5000`. If you see the text, Flask is wired up correctly. Delete or overwrite this temporary content once confirmed.

---

## 2. Backend Implementation

### 2.1 Overview of Backend Files

The backend is organised into separate files, each owning a single responsibility. This is not mandatory for Flask but makes the code far easier to navigate and test:

| File | What it does |
|---|---|
| `app.py` | Creates the Flask app, registers all routes, and starts the server. |
| `database.py` | Opens the SQLite connection and provides reusable query helper functions. |
| `models.py` | Defines the shape of data (Customer, Account, Transaction) as Python classes or named tuples. |
| `auth.py` | Handles login logic, session creation, logout, and the route-guard decorator. |
| `transactions.py` | Contains deposit and withdrawal business logic. |
| `seed.py` | A one-time script that inserts demo customers into the database. |

---

### 2.2 `database.py` — Setting Up the Data Layer

The purpose of this file is to centralise all interactions with SQLite so that no other file ever imports `sqlite3` directly.

**What to implement:**

1. **Connection function** — Write a function that opens a connection to `bank.db` (SQLite creates the file automatically if it does not exist). Configure the connection so it returns rows as dictionary-like objects, making it easy to access columns by name rather than by index.

2. **Initialisation function** — Write a function that creates the three tables (customers, accounts, transactions) if they do not already exist. This function is called once when the app starts, making the app self-bootstrapping.

3. **Query helper functions** — Write small, focused functions for each database operation the rest of the app needs:
   - Fetch a customer record by username.
   - Fetch the account balance for a given customer ID.
   - Update the balance of an account.
   - Insert a new transaction record (type, amount, timestamp).

By centralising all SQL here, the rest of the codebase never needs to know the database structure — it just calls these helper functions.

---

### 2.3 `models.py` — Defining Data Shapes

Models describe what a piece of data looks like in Python. You do not need a heavy ORM framework. Simple Python classes or `dataclasses` work well.

Define three models:

- **Customer** — holds `id`, `username`, `password_hash`, and `full_name`.
- **Account** — holds `id`, `customer_id` (foreign key), and `balance`.
- **Transaction** — holds `id`, `account_id`, `type` (deposit or withdrawal), `amount`, and `created_at`.

These models are used by the helper functions in `database.py` to package data cleanly before passing it to route handlers.

---

### 2.4 `auth.py` — Authentication Logic

This file is the security backbone of the application. It should contain the following pieces:

#### Login Service Function

When a customer submits the login form, this function:
1. Receives the submitted username and password.
2. Calls the database helper to look up the customer by username.
3. If no customer is found, returns a failure result (do not reveal whether the username or password is wrong — just say "invalid credentials").
4. If a customer is found, uses Werkzeug's `check_password_hash` utility to compare the submitted password against the stored hash. Werkzeug handles the secure comparison; you never compare plain text to a hash manually.
5. If the hash check passes, returns the customer record so the caller (the route handler) can create a session.

#### Session Creation

After a successful login, the route handler stores the customer's `id` and `full_name` into Flask's `session` dictionary. Flask automatically signs and encrypts this session using the app's `SECRET_KEY`, so it cannot be tampered with by the browser.

#### `login_required` Decorator

A decorator is a function that wraps another function to add behaviour before and after it runs. Write a `login_required` decorator that:
1. Checks whether `customer_id` is present in the current Flask session.
2. If yes, allows the wrapped route function to run normally.
3. If no, immediately redirects the user to the login page.

Apply this decorator to every route that requires authentication (dashboard, deposit, withdraw). This means you write the protection logic once and reuse it everywhere.

#### Logout Function

Logout simply calls Flask's `session.clear()` to wipe all session data, then redirects to the login page. There is no database operation needed — the session exists only in the signed cookie, and clearing it is sufficient.

---

### 2.5 `transactions.py` — Deposit and Withdrawal Logic

This file contains the business rules for moving money. Keep these functions free of any Flask or HTTP concepts — they should only receive plain data, apply rules, and return a result.

#### Deposit Logic

1. Receive the customer's account ID and the amount they wish to deposit.
2. Validate the amount (covered in detail in Section 5).
3. Fetch the current balance from the database.
4. Add the deposit amount to the current balance.
5. Write the new balance back to the database (update the account row).
6. Insert a transaction record of type "deposit" with the amount and current timestamp.
7. Return a success result to the caller.

#### Withdrawal Logic

1. Receive the customer's account ID and the amount they wish to withdraw.
2. Validate the amount (covered in detail in Section 5).
3. Fetch the current balance from the database.
4. Check that the balance is greater than or equal to the withdrawal amount. If not, return a failure result with an "insufficient funds" message.
5. Subtract the withdrawal amount from the current balance.
6. Write the new balance back to the database.
7. Insert a transaction record of type "withdrawal" with the amount and current timestamp.
8. Return a success result to the caller.

> The balance check and the update should conceptually be treated as a single atomic operation. In SQLite, wrapping them in a transaction ensures the database is never left in a half-updated state.

---

### 2.6 `app.py` — Routes and Controllers

`app.py` is the entry point and the only file that knows about Flask's HTTP layer. Each route function is a thin **controller** — it reads the incoming request, calls a service function (from `auth.py` or `transactions.py`), and renders a template or issues a redirect.

#### Route: `GET /` (Root)

Simply redirect to `/login`. This ensures the root URL is never a dead end.

#### Route: `GET /login`

Render `login.html`. If the customer is already logged in (session contains `customer_id`), redirect directly to `/dashboard` to avoid showing the login form to an already-authenticated user.

#### Route: `POST /login`

1. Read `username` and `password` from the submitted form data.
2. Call the login service function in `auth.py`.
3. If login fails, re-render `login.html` and pass an error message to the template.
4. If login succeeds, store the customer's identity in the session, then redirect to `/dashboard`.

#### Route: `GET /dashboard` _(protected)_

Apply the `login_required` decorator. In the handler:
1. Read the `customer_id` from the session.
2. Call the database helper to fetch the current balance for that customer.
3. Render `dashboard.html`, passing the customer's name and balance as template variables.

#### Route: `GET /deposit` _(protected)_

Apply `login_required`. Simply render the `deposit.html` form.

#### Route: `POST /deposit` _(protected)_

1. Read the `amount` field from the submitted form.
2. Call the deposit service function in `transactions.py`.
3. If validation or the service fails, re-render the deposit form with an error message.
4. If successful, redirect to `/dashboard` with a success flash message.

#### Route: `GET /withdraw` _(protected)_

Apply `login_required`. Render `withdraw.html`, and pass the current balance to the template so the form can show the customer their available funds.

#### Route: `POST /withdraw` _(protected)_

1. Read the `amount` field from the submitted form.
2. Call the withdrawal service function in `transactions.py`.
3. If the service returns an "insufficient funds" error, re-render the withdrawal form with that error message.
4. If successful, redirect to `/dashboard` with a success flash message.

#### Route: `POST /logout` _(protected)_

Call the logout function from `auth.py`, then redirect to `/login`.

---

### 2.7 Session Management

Flask sessions work through a signed cookie stored in the user's browser. The cookie is signed using the app's `SECRET_KEY`, which means any tampering makes the signature invalid and Flask discards the session.

**Key points:**

- Set `app.secret_key` to a long, random string. In development you can hard-code it; in production it must come from an environment variable or secrets manager.
- Store only the minimum necessary data in the session — the customer's `id` and `full_name` are enough. Never store the password or full account data in the session.
- Flask sessions are not stored server-side by default (they live entirely in the signed cookie). This is fine for this application's scale.

---

### 2.8 Error Handling

Rather than letting Flask show its default error pages, register custom handlers for the two most common HTTP errors:

- **404 Not Found** — render a friendly "Page not found" page.
- **500 Internal Server Error** — render a generic "Something went wrong" page.

Additionally, in route handlers, always handle the case where a database call returns nothing (e.g., the customer's account row is missing). Redirect to a safe page with a message rather than letting an unhandled exception crash the server.

---

### 2.9 `seed.py` — Populating Demo Data

This is a standalone script (not part of the Flask app). When run directly with `python seed.py`, it:

1. Connects to `bank.db`.
2. Inserts two or three demo customer records with hashed passwords (using Werkzeug's `generate_password_hash`).
3. Creates an account row for each customer with a starting balance.
4. Prints the demo usernames and plain-text passwords to the terminal for reference.

Run this script once after the database tables are created. Running it a second time should be safe — it should check whether the demo records already exist before inserting, so it never creates duplicates.

---

## 3. Frontend Implementation

### 3.1 How Flask Serves the Frontend

Flask's Jinja2 template engine renders HTML files stored in the `templates/` folder. When a route handler calls `render_template('dashboard.html', balance=1500)`, Jinja2 reads that file and substitutes any template variables (`{{ balance }}`) with the real values before sending the HTML to the browser.

Static files (CSS, JS, images) are served from the `static/` folder. Flask automatically maps any request for `/static/<filename>` to that folder.

Because Flask controls where templates and static files are found, you must configure these paths when creating the Flask app:
- Point the `template_folder` parameter to `FRONTEND/templates/`.
- Point the `static_folder` parameter to `FRONTEND/static/`.

---

### 3.2 Bootstrap Layout Approach

Every page should share a consistent visual structure. The recommended approach is to create a **base template** (`base.html`) that contains:

- The HTML boilerplate (`<html>`, `<head>`, `<body>` tags).
- The Bootstrap CSS link (loaded from the Bootstrap CDN).
- The navigation bar with links to Dashboard and Logout (hidden on the login page).
- A main content block that child templates fill in.
- A Flash messages area that displays any success or error messages from the backend.

All other templates (`login.html`, `dashboard.html`, etc.) extend `base.html` and only define their own unique content block. This means you write the navbar and Bootstrap imports exactly once.

---

### 3.3 Login Page (`login.html`)

**Purpose:** Collect the customer's username and password and submit them to the backend.

**Layout approach:**
- Centre a card on the screen using Bootstrap's grid (e.g., `col-md-4 offset-md-4`).
- Inside the card, place the bank's name as a heading, then the login form below it.
- The form has two input fields (username, password) and a submit button.
- The `action` attribute of the form points to `/login` and the `method` is `POST`.
- If the backend passes an error message to the template, display it as a Bootstrap danger alert above the form.

**What this page does NOT do:**
- It does not validate credentials — that is entirely the backend's job.
- It does not redirect after login — the backend issues the redirect.

---

### 3.4 Dashboard Page (`dashboard.html`)

**Purpose:** Give the logged-in customer an overview of their account.

**Layout approach:**
- Extends `base.html` so the navbar is visible.
- Display a welcome heading using the customer's name (passed from the backend as a template variable).
- Show the current account balance inside a prominent card or info box. Format it as a monetary value (e.g., two decimal places).
- Provide two clearly labelled action buttons — "Deposit Funds" and "Withdraw Funds" — that link to their respective pages.
- If the backend flashes a success message (after a deposit or withdrawal), the base template's flash area will display it automatically.

---

### 3.5 Deposit Form (`deposit.html`)

**Purpose:** Allow the customer to enter an amount to deposit.

**Layout approach:**
- Extends `base.html`.
- A simple card with a single numeric input field labelled "Amount to Deposit".
- A submit button that posts the form to `/deposit`.
- An optional "Back to Dashboard" link.
- If the backend passes an error message (e.g., invalid amount), display it as a Bootstrap danger alert above the form.

**Note:** The amount input should use `type="number"` with `min="0.01"` and `step="0.01"` as HTML attributes. This provides basic client-side hints but does not replace server-side validation.

---

### 3.6 Withdraw Form (`withdraw.html`)

**Purpose:** Allow the customer to enter an amount to withdraw.

**Layout approach:**
- Nearly identical to `deposit.html`, with the heading changed to "Withdraw Funds".
- Additionally, display the customer's current available balance on this page (passed from the backend), so the customer knows the maximum they can withdraw before submitting the form.
- If the backend returns an "insufficient funds" error, display it as a Bootstrap danger alert.

---

## 4. Integration Steps

### 4.1 Connecting Flask to SQLite

The connection between Flask and SQLite is managed entirely in `database.py`. The integration requires the following steps in the correct order:

1. **On app startup**, call the database initialisation function. This should happen inside `app.py` before the server starts listening for requests. This ensures the tables exist before any route is hit.

2. **Per request**, open a fresh database connection at the start of a request and close it when the request ends. Flask provides two hooks for this — `before_request` and `teardown_request` — which you register in `app.py`. This pattern prevents connection leaks.

3. **Flask's application context** (`g` object) is the standard place to store the per-request database connection. When a helper function in `database.py` needs a connection, it reads it from `g` if one already exists, or opens a new one if it does not. This ensures exactly one connection per request.

---

### 4.2 Connecting Frontend Forms to Backend Routes

HTML forms connect to Flask routes through two attributes:

- `action` — the URL path the form data is sent to (e.g., `/login`, `/deposit`).
- `method` — the HTTP method. Use `POST` for any action that changes state (login, deposit, withdraw, logout). Use `GET` only for read-only requests.

Ensure every form's `action` attribute exactly matches a route registered in `app.py`. A mismatch will result in a 404 error.

---

### 4.3 Passing Data from Backend to Frontend

Flask's `render_template` function accepts keyword arguments that become available as variables inside the HTML template. For example:

- Pass the customer's name and balance to `dashboard.html`.
- Pass an error message string to `login.html` when credentials are wrong.
- Pass the current balance to `withdraw.html` so the customer can see their limit.

Inside the Jinja2 template, use `{{ variable_name }}` to output a variable's value, and `{% if variable_name %}` to conditionally show content (like an error alert).

---

### 4.4 Flash Messages

Flask has a built-in flash message system. After a successful deposit or withdrawal, instead of passing a success string directly to `render_template`, the route handler calls `flash("Deposit successful!")` and then redirects to `/dashboard`. On the next request, `dashboard.html` (via `base.html`) retrieves the flashed messages and displays them.

This follows the Post-Redirect-Get pattern, which prevents the browser from re-submitting the form if the user refreshes the page after a transaction.

---

## 5. Validation Rules

Validation must happen on the **backend** for every input. Frontend validation (HTML attributes, JavaScript) is a convenience for the user but is not security — it can be bypassed.

### 5.1 Login Validation

| Rule | What to check | Error to show |
|---|---|---|
| Username not empty | `username` field is not blank or whitespace only | "Username is required." |
| Password not empty | `password` field is not blank | "Password is required." |
| Credentials correct | Username exists AND password hash matches | "Invalid username or password." |

> Use a single generic error message for failed credentials. Never tell the user specifically whether the username or password was wrong — that gives an attacker information about which accounts exist.

---

### 5.2 Balance Validation (on Withdrawal)

| Rule | What to check | Error to show |
|---|---|---|
| Account exists | A valid account row is found for the logged-in customer | Redirect to dashboard with a session error. |
| Sufficient balance | `current_balance >= withdrawal_amount` | "Insufficient funds. Your balance is X." |

---

### 5.3 Deposit Checks

| Rule | What to check | Error to show |
|---|---|---|
| Amount present | The `amount` field is not empty | "Please enter an amount." |
| Amount is numeric | The value can be parsed as a float without an exception | "Amount must be a number." |
| Amount is positive | `amount > 0` | "Deposit amount must be greater than zero." |
| Amount is reasonable | Optionally cap at a maximum (e.g., 1,000,000) to prevent overflow | "Amount exceeds the maximum allowed deposit." |

---

### 5.4 Withdrawal Checks

| Rule | What to check | Error to show |
|---|---|---|
| Amount present | The `amount` field is not empty | "Please enter an amount." |
| Amount is numeric | The value can be parsed as a float without an exception | "Amount must be a number." |
| Amount is positive | `amount > 0` | "Withdrawal amount must be greater than zero." |
| Sufficient balance | `current_balance >= amount` | "Insufficient funds." |

> Apply deposit and withdrawal checks in the order listed. Stop at the first failure and return that error. Do not accumulate all errors — return the first one encountered.

---

## 6. Testing

### 6.1 Unit Tests

Unit tests verify individual functions in isolation, without a running Flask server or a real database.

**What to unit test:**

| Function | What to assert |
|---|---|
| `auth.py` login service | Returns failure when username does not exist. |
| `auth.py` login service | Returns failure when password is wrong. |
| `auth.py` login service | Returns success when credentials are correct. |
| `transactions.py` deposit | Returns success and correct new balance for a valid amount. |
| `transactions.py` deposit | Returns failure for a zero or negative amount. |
| `transactions.py` withdrawal | Returns success and correct new balance when funds are sufficient. |
| `transactions.py` withdrawal | Returns failure with "insufficient funds" when amount exceeds balance. |

**How to run:** Use Python's built-in `unittest` module or install `pytest`. Tests should use in-memory SQLite (`:memory:`) rather than the real `bank.db` file so they run fast and leave no side effects.

---

### 6.2 Integration Tests

Integration tests verify that the Flask routes and the database work correctly together. Flask ships with a test client that simulates HTTP requests without a real browser.

**What to integration test:**

| Scenario | Expected result |
|---|---|
| `GET /dashboard` without a session | Redirects to `/login` (302). |
| `POST /login` with valid credentials | Redirects to `/dashboard` (302) and session contains `customer_id`. |
| `POST /login` with invalid credentials | Returns 200 with `login.html` and an error message in the response body. |
| `POST /deposit` with a valid amount | Redirects to `/dashboard` (302) and the balance in the database has increased. |
| `POST /withdraw` with an amount exceeding balance | Returns 200 with `withdraw.html` and an "insufficient funds" message. |
| `POST /logout` | Clears the session and redirects to `/login` (302). |

**How to run:** Use `pytest` with Flask's test client. Set up a fresh in-memory database before each test so tests are independent and do not affect each other.

---

### 6.3 Manual Testing Checklist

After automated tests pass, walk through the full application manually in a browser to catch any visual or flow issues that automated tests may miss.

#### Authentication Flow

- [ ] Navigate to `http://127.0.0.1:5000` — confirm it redirects to `/login`.
- [ ] Submit the login form with a blank username — confirm an error message appears.
- [ ] Submit the login form with a wrong password — confirm the generic error message appears.
- [ ] Submit with valid credentials — confirm redirect to the dashboard.
- [ ] While logged in, navigate directly to `/login` — confirm it redirects back to the dashboard.
- [ ] Click Logout — confirm the session is cleared and you are on the login page.
- [ ] After logout, navigate directly to `/dashboard` — confirm redirect to `/login`.

#### Deposit Flow

- [ ] From the dashboard, click "Deposit Funds".
- [ ] Submit the deposit form with a blank amount — confirm error.
- [ ] Submit with a negative amount — confirm error.
- [ ] Submit with a valid amount — confirm redirect to dashboard with success message.
- [ ] Confirm the balance on the dashboard has increased by the deposited amount.

#### Withdrawal Flow

- [ ] From the dashboard, click "Withdraw Funds".
- [ ] Confirm the current balance is displayed on the withdrawal page.
- [ ] Submit with an amount greater than the balance — confirm "insufficient funds" error.
- [ ] Submit with a valid amount — confirm redirect to dashboard with success message.
- [ ] Confirm the balance on the dashboard has decreased by the withdrawn amount.

#### Edge Cases

- [ ] Attempt to deposit "abc" (non-numeric) — confirm error.
- [ ] Attempt to withdraw 0 — confirm error.
- [ ] Open the deposit page in two browser tabs and submit both — confirm the balance is correct (no double-credit or inconsistency).

---

## 7. Deployment

### 7.1 Running the App Locally

Once the backend and frontend are implemented:

1. Activate the virtual environment (see Section 1.3).
2. Navigate to the `BACKEND/` folder.
3. If running for the first time, run `python seed.py` to populate the database with demo customers.
4. Run `python app.py`. Flask will start its built-in development server and print the local URL (typically `http://127.0.0.1:5000`).
5. Open that URL in a browser.

**Environment variable for secret key:**
Set a `SECRET_KEY` environment variable before starting the app. In development, you can set it inline:
- On Windows PowerShell: `$env:SECRET_KEY = "dev-secret-key-change-me"`
- On macOS/Linux: `export SECRET_KEY="dev-secret-key-change-me"`

Then read it in `app.py` using `os.environ.get('SECRET_KEY', 'fallback-dev-key')`.

---

### 7.2 Development Mode vs. Production Mode

Flask's built-in server is **development only**. It is single-threaded, not designed for concurrent users, and exposes a debug console that would be a critical security vulnerability in production.

| Concern | Development | Production |
|---|---|---|
| Server | Flask built-in (`app.run()`) | Gunicorn or uWSGI |
| Debug mode | `debug=True` (auto-reload, error pages) | `debug=False` (never enable in prod) |
| Secret key | Hard-coded for convenience | Injected via environment variable |
| Database | SQLite file | PostgreSQL or MySQL for concurrency |
| HTTPS | Not needed locally | Required; use a reverse proxy like Nginx |

---

### 7.3 Production Considerations

The following items are out of scope for the workshop but must be addressed before any real-world deployment:

#### WSGI Server
Replace `app.run()` with a production WSGI server such as **Gunicorn**. Gunicorn handles multiple concurrent requests and integrates with Nginx or a cloud platform's load balancer.

#### Reverse Proxy (Nginx)
Place Nginx in front of Gunicorn. Nginx serves static files directly (faster than Flask), handles SSL termination, and forwards dynamic requests to Gunicorn.

#### HTTPS / TLS
All traffic must be encrypted. Obtain a certificate (free via Let's Encrypt) and configure it in Nginx.

#### Environment-Based Configuration
Never hard-code `SECRET_KEY`, database paths, or any credential in source code. Use environment variables or a `.env` file (loaded with the `python-dotenv` package) that is never committed to version control.

#### CSRF Protection
Forms that perform state changes (login, deposit, withdraw) should include a CSRF token. The `Flask-WTF` extension handles this automatically.

#### Session Expiry
Set a `PERMANENT_SESSION_LIFETIME` to automatically expire sessions after a period of inactivity (e.g., 30 minutes), preventing forgotten browser tabs from staying logged in indefinitely.

#### Database Upgrade
SQLite is adequate for single-user or low-concurrency scenarios. For a multi-user production banking system, migrate to **PostgreSQL** and use an ORM like SQLAlchemy to manage schema migrations cleanly.

#### Logging
Replace `print()` statements with Python's `logging` module. In production, write logs to a file or a centralised logging service so issues can be diagnosed without console access.

---

*End of Step-by-Step Implementation Guide*
