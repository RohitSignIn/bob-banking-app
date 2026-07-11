# SecureBank — Banking Web Application

A full-stack banking web application built with Python Flask (backend), Bootstrap 5 (frontend), and SQLite (database).

---

## Features

| Feature | URL |
|---|---|
| Customer Login | `/login` |
| Dashboard with balance | `/dashboard` |
| Deposit funds | `/deposit` |
| Withdraw funds | `/withdraw` |
| Logout | POST `/logout` |

---

## Project Structure

```
banking-workshop/
├── FRONTEND/
│   ├── templates/          HTML pages (Jinja2)
│   │   ├── base.html       Shared layout, navbar, flash messages
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── deposit.html
│   │   ├── withdraw.html
│   │   ├── 404.html
│   │   └── 500.html
│   └── static/
│       ├── css/styles.css
│       └── js/scripts.js
│
├── BACKEND/
│   ├── app.py              Flask app entry point + all routes
│   ├── auth.py             Login, session, login_required decorator
│   ├── transactions.py     Deposit and withdrawal business logic
│   ├── database.py         SQLite connection + query helpers
│   ├── models.py           Data model dataclasses
│   ├── seed.py             One-time demo data seeder
│   ├── requirements.txt    Python dependencies
│   ├── bank.db             SQLite database (auto-created)
│   ├── conftest.py         Pytest fixtures (in-memory DB injection)
│   ├── test_auth.py        Unit tests — authentication
│   ├── test_transactions.py Unit tests — deposit/withdrawal logic
│   └── test_routes.py      Integration tests — HTTP routes
│
├── IMPLEMENTATION_PLAN.md
├── STEP_BY_STEP_IMPLEMENTATION_GUIDE.md
└── README.md               This file
```

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip

### 1. Create and activate a virtual environment

```powershell
# Windows PowerShell
cd BACKEND
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
cd BACKEND
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Seed the database with demo accounts

```bash
python seed.py
```

This creates `bank.db` and inserts three demo customers:

| Name | Username | Password | Opening Balance |
|---|---|---|---|
| Alice Johnson | `alice` | `alice123` | £5,000.00 |
| Bob Williams | `bob` | `bob456` | £2,500.00 |
| Carol Davis | `carol` | `carol789` | £10,000.00 |

### 4. Set the secret key (recommended)

```powershell
# Windows PowerShell
$env:SECRET_KEY = "my-strong-secret-key-change-me"
```

```bash
# macOS / Linux
export SECRET_KEY="my-strong-secret-key-change-me"
```

If not set, a default development key is used automatically.

### 5. Run the application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## Running the Tests

```bash
# From the BACKEND/ folder, with the virtual environment active
python -m pytest test_auth.py test_transactions.py test_routes.py -v
```

Expected: **48 passed**.

Tests use an in-memory SQLite database — they never touch the real `bank.db`.

---

## Architecture Overview

```
Browser (HTML + Bootstrap)
        │  HTTP (form POST / GET)
        ▼
Flask App  (BACKEND/app.py)
  ├── auth.py          — login, sessions, route guard
  ├── transactions.py  — deposit / withdrawal rules
  └── database.py      — SQLite helpers
        │  SQL queries
        ▼
SQLite  (BACKEND/bank.db)
  ├── customers
  ├── accounts
  └── transactions
```

---

## Security Notes

- Passwords are stored as bcrypt-compatible hashes via Werkzeug's `generate_password_hash`.
- The Flask session is a signed cookie — tamper-evident, not readable without the `SECRET_KEY`.
- All input validation is enforced on the **backend** (frontend hints are convenience only).
- Sessions expire after 30 minutes of inactivity.
- Custom 404 and 500 error pages prevent stack-trace leakage.

---

## Production Considerations

For a real deployment, the following additional steps are required:

1. **WSGI server** — replace `python app.py` with `gunicorn app:app`.
2. **Reverse proxy** — use Nginx for static files and SSL termination.
3. **HTTPS / TLS** — required for all traffic; use Let's Encrypt.
4. **CSRF protection** — add `Flask-WTF` for all state-changing forms.
5. **Environment config** — read `SECRET_KEY` and DB path from environment variables only.
6. **Database** — upgrade to PostgreSQL for multi-user concurrent access.
7. **Logging** — replace `print()` with Python `logging` module.

See [`STEP_BY_STEP_IMPLEMENTATION_GUIDE.md`](STEP_BY_STEP_IMPLEMENTATION_GUIDE.md) Section 7 for full details.
