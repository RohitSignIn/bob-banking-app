# Banking Web Application — Implementation Plan

> **Document type:** High-level planning only.
> No database schema, SQL scripts, API contracts, or step-by-step code details are included.

---

## Table of Contents

1. [Solution Overview](#1-solution-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Design](#3-component-design)
4. [Folder Structure](#4-folder-structure)
5. [Module Breakdown](#5-module-breakdown)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## 1. Solution Overview

### 1.1 Objective

Deliver a lightweight, browser-based banking web application that allows registered customers to securely log in, view their account balance, and perform basic fund transactions (deposit and withdrawal) through a clean, responsive interface.

### 1.2 Scope

| In Scope | Out of Scope |
|---|---|
| Customer login and session management | Admin / bank-staff portal |
| Personal dashboard with account summary | Multi-currency support |
| View current account balance | Loan or credit features |
| Deposit funds | Inter-account transfers |
| Withdraw funds | Third-party payment integrations |
| Logout | Mobile native application |

### 1.3 Users

| User Type | Description |
|---|---|
| **Customer** | A registered bank customer who logs in to view and manage their own account. |

> Only one user role is in scope. No admin or super-user role is planned for this iteration.

### 1.4 Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | A customer can log in using a username and password. |
| FR-02 | Invalid login credentials are rejected with a clear error message. |
| FR-03 | An authenticated customer can view a personalised dashboard. |
| FR-04 | An authenticated customer can view their current account balance. |
| FR-05 | An authenticated customer can deposit a positive monetary amount. |
| FR-06 | An authenticated customer can withdraw an amount up to their available balance. |
| FR-07 | A customer can log out, which terminates the active session. |
| FR-08 | Unauthenticated users are redirected to the login page. |

### 1.5 Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Security** — Passwords must be stored hashed; sessions must be invalidated on logout. |
| NFR-02 | **Usability** — UI must be responsive and usable on modern desktop browsers. |
| NFR-03 | **Simplicity** — No build pipeline required; the app must run with a single Python command. |
| NFR-04 | **Portability** — SQLite is used so the application requires no external database service. |
| NFR-05 | **Maintainability** — Frontend and backend code must be kept in separate, clearly named folders. |

### 1.6 Assumptions

- A small number of pre-seeded customer accounts is sufficient for demonstration.
- All monetary values are treated as a single unnamed currency (no forex required).
- The application will be run locally in a development/workshop context; production hardening (HTTPS, rate-limiting, CSRF tokens) is considered future work.
- Bootstrap is loaded from a CDN; no local asset bundling is needed.
- Python 3.x and Flask are available in the target environment.

---

## 2. High-Level Architecture

### 2.1 Architecture Overview

The application follows a classic **three-tier web architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT BROWSER                      │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │   FRONTEND  (FRONTEND/)                         │   │
│   │   HTML pages + Bootstrap CSS/JS                 │   │
│   │   login · dashboard · deposit · withdraw        │   │
│   └──────────────────┬──────────────────────────────┘   │
└──────────────────────│──────────────────────────────────┘
                       │  HTTP Requests
                       │  (form submissions / page requests)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                BACKEND  (BACKEND/)                      │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │   Python Flask Application                      │   │
│   │   Routes · Session Management · Business Logic  │   │
│   └──────────────────┬──────────────────────────────┘   │
└──────────────────────│──────────────────────────────────┘
                       │  SQL Queries (via ORM / sqlite3)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                DATABASE  (BACKEND/)                     │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │   SQLite File  (bank.db)                        │   │
│   │   Customers table · Accounts table              │   │
│   │   Transactions table                            │   │
│   └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Frontend → Backend → Database Interaction

```
Browser (HTML Form)
      │
      │  POST /login  (username, password)
      ▼
Flask Route (/login)
      │
      │  Query: fetch customer by username
      ▼
SQLite (customers table)
      │
      │  Row returned → verify hashed password
      ▼
Flask Session created → redirect to /dashboard
      │
      ▼
Browser renders dashboard.html
```

The same pattern applies for deposit, withdrawal, and logout flows — browser submits form → Flask validates and processes → SQLite is updated → Flask redirects back with a result.

### 2.3 Request Lifecycle

| Step | Actor | Action |
|------|--------|--------|
| 1 | Browser | User submits a form or navigates to a URL |
| 2 | Flask Router | Matches the URL to the correct route handler |
| 3 | Auth Guard | Checks whether a valid session exists; redirects if not |
| 4 | Business Logic | Validates inputs and applies rules (e.g., sufficient balance) |
| 5 | Data Layer | Reads from or writes to the SQLite database |
| 6 | Flask Response | Renders an HTML template or issues an HTTP redirect |
| 7 | Browser | Displays the resulting page to the customer |

---

## 3. Component Design

### 3.1 Frontend Responsibilities

The frontend layer is purely presentational. It is responsible for:

- **Rendering pages** — Login form, Dashboard summary, Deposit form, Withdrawal form.
- **User input collection** — HTML forms that capture credentials and transaction amounts.
- **Visual feedback** — Displaying success/error messages passed from the backend (via template variables or query parameters).
- **Responsive layout** — Using Bootstrap grid and components so pages work across common screen sizes.
- **Navigation** — Header/navbar with links to Dashboard and Logout.

The frontend does **not** contain business logic. It trusts the backend to validate all inputs and enforce all rules.

### 3.2 Backend Responsibilities

The backend layer owns all logic and security. It is responsible for:

- **Routing** — Mapping URL paths and HTTP methods to handler functions.
- **Authentication** — Verifying credentials at login, creating and destroying sessions.
- **Authorisation** — Protecting all routes that require a logged-in session.
- **Business Logic** — Enforcing deposit/withdrawal rules (positive amounts, sufficient balance).
- **Data Access** — All read/write operations against the SQLite database.
- **Response Generation** — Rendering Jinja2 HTML templates with dynamic data.

### 3.3 Database Responsibilities

The SQLite database is the single source of truth for persistent data. It is responsible for:

- **Storing customer identity** — Usernames and hashed passwords.
- **Storing account balances** — Current balance per customer account.
- **Recording transaction history** — Each deposit and withdrawal event with timestamp and amount.
- **Data integrity** — Enforcing constraints so that invalid states (e.g., negative balance) cannot be persisted.

---

## 4. Folder Structure

```
banking-workshop/
│
├── FRONTEND/                        ← All browser-side assets
│   ├── templates/                   ← Jinja2 / HTML page templates
│   │   ├── login.html               ← Customer login page
│   │   ├── dashboard.html           ← Post-login account overview
│   │   ├── deposit.html             ← Deposit funds form
│   │   └── withdraw.html            ← Withdraw funds form
│   └── static/                      ← Static assets served by Flask
│       ├── css/
│       │   └── styles.css           ← Custom styles (minimal; Bootstrap handles most)
│       └── js/
│           └── scripts.js           ← Optional minor client-side helpers
│
├── BACKEND/                         ← All server-side code and data
│   ├── app.py                       ← Flask application entry point; route definitions
│   ├── auth.py                      ← Authentication helpers (login, session, logout)
│   ├── transactions.py              ← Deposit and withdrawal business logic
│   ├── database.py                  ← Database connection, initialisation, query helpers
│   ├── models.py                    ← Data model definitions (Customer, Account, Transaction)
│   ├── seed.py                      ← One-time script to seed demo customer accounts
│   ├── requirements.txt             ← Python dependencies (Flask, etc.)
│   └── bank.db                      ← SQLite database file (auto-created on first run)
│
├── IMPLEMENTATION_PLAN.md           ← This document
└── README.md                        ← Project overview and run instructions
```

### Folder Responsibility Summary

| Path | Responsibility |
|---|---|
| `FRONTEND/templates/` | HTML pages rendered by Flask's Jinja2 engine |
| `FRONTEND/static/` | CSS and JavaScript files served directly to the browser |
| `BACKEND/app.py` | Application factory, Flask instance, all route registrations |
| `BACKEND/auth.py` | Login validation, session creation, logout, route guard decorator |
| `BACKEND/transactions.py` | Deposit and withdrawal logic with balance checks |
| `BACKEND/database.py` | SQLite connection management and reusable query helpers |
| `BACKEND/models.py` | Lightweight data-model definitions (no ORM framework required) |
| `BACKEND/seed.py` | Populates the database with demo customers for workshop use |
| `BACKEND/bank.db` | The SQLite file; created automatically; not committed to source control |

---

## 5. Module Breakdown

### 5.1 Authentication Module

**Purpose:** Manage the full identity lifecycle — from credential verification to session termination.

| Concern | Detail |
|---|---|
| Login page | Renders username/password form; displays error on failure |
| Credential check | Compares submitted password against stored hash |
| Session creation | Stores customer identity in a server-side Flask session on success |
| Route protection | A guard decorator checks for a valid session before every protected route |
| Logout | Clears the session and redirects to the login page |

**Key pages/routes:** `/login` (GET + POST), `/logout` (POST)

---

### 5.2 Dashboard Module

**Purpose:** Provide the customer with a personalised landing page after login.

| Concern | Detail |
|---|---|
| Welcome message | Displays the customer's name from session data |
| Account snapshot | Shows current balance retrieved from the database |
| Navigation | Links to Deposit, Withdraw, and Logout actions |
| Access control | Redirects to login if no active session exists |

**Key pages/routes:** `/dashboard` (GET)

---

### 5.3 Account Management Module

**Purpose:** Display detailed account information available to the authenticated customer.

| Concern | Detail |
|---|---|
| Balance display | Fetches and renders the real-time account balance |
| Account identity | Shows account number or identifier for context |
| Read-only view | No mutations occur in this module; purely informational |

**Key pages/routes:** Embedded within `/dashboard` (GET) or a dedicated `/account` (GET)

---

### 5.4 Transactions Module

**Purpose:** Handle fund movements into and out of the customer's account.

| Sub-feature | Detail |
|---|---|
| **Deposit** | Accepts a positive amount; adds it to the current balance; records the event |
| **Withdraw** | Accepts a positive amount; checks sufficient balance; deducts and records the event |
| Input validation | Rejects zero, negative, or non-numeric amounts with a clear error message |
| Insufficient funds | Returns an error if the withdrawal amount exceeds the available balance |
| Confirmation | Redirects back to the dashboard with a success message on completion |

**Key pages/routes:** `/deposit` (GET + POST), `/withdraw` (GET + POST)

---

## 6. Implementation Roadmap

### 6.1 Development Phases

```
Phase 1 — Project Scaffolding
  └─ Create folder structure (FRONTEND/, BACKEND/)
  └─ Initialise Flask app and confirm it runs
  └─ Wire up static files and template directories

Phase 2 — Database Setup
  └─ Define data models (Customer, Account, Transaction)
  └─ Write database initialisation logic
  └─ Seed demo customer accounts for testing

Phase 3 — Authentication
  └─ Build login page (HTML + Bootstrap)
  └─ Implement login route with credential validation
  └─ Implement session management and route guard
  └─ Implement logout route

Phase 4 — Dashboard
  └─ Build dashboard page showing balance and customer name
  └─ Connect dashboard to live balance data from the database
  └─ Add navigation bar with Deposit, Withdraw, Logout links

Phase 5 — Transactions
  └─ Build deposit page and route (GET + POST)
  └─ Build withdrawal page and route (GET + POST)
  └─ Add input validation and business rules
  └─ Show success/error feedback after each transaction

Phase 6 — Integration & Polish
  └─ End-to-end flow testing (login → transact → logout)
  └─ Apply consistent Bootstrap styling across all pages
  └─ Handle edge cases: double-submit, session timeout, invalid input
```

### 6.2 Estimated Effort

| Phase | Relative Effort |
|---|---|
| Phase 1 — Scaffolding | Low |
| Phase 2 — Database Setup | Low–Medium |
| Phase 3 — Authentication | Medium |
| Phase 4 — Dashboard | Low |
| Phase 5 — Transactions | Medium |
| Phase 6 — Integration & Polish | Medium |

> Effort is expressed relatively (Low / Medium / High) as this is a planning document. Actual duration depends on team size and familiarity with Flask.

### 6.3 Dependencies

```
Phase 1
  └─ No external dependencies; must complete before all other phases.

Phase 2
  └─ Depends on: Phase 1 (folder structure and Flask app exist)

Phase 3
  └─ Depends on: Phase 2 (customer records must exist in the database)

Phase 4
  └─ Depends on: Phase 3 (dashboard is only reachable after login)

Phase 5
  └─ Depends on: Phase 4 (transactions initiated from the dashboard)

Phase 6
  └─ Depends on: Phases 3–5 (all features must be built before integration testing)
```

### 6.4 Risk Considerations

| Risk | Mitigation |
|---|---|
| Session security misconfiguration | Use Flask's built-in signed session cookies; set a strong `SECRET_KEY` |
| Balance going negative | Enforce balance check in backend before any withdrawal is committed |
| SQLite concurrency | Acceptable for a single-user workshop scenario; upgrade to PostgreSQL for multi-user production use |
| Bootstrap CDN unavailable offline | Keep a local copy of Bootstrap in `FRONTEND/static/` as a fallback |

---

*End of Implementation Plan*
