"""
test_routes.py
--------------
Integration tests for Flask routes using Flask's built-in test client.

The `client` fixture is provided by conftest.py — it injects a fresh
in-memory database for every test so tests are fully isolated from
each other and from the real bank.db file.

Covers:
  - Unauthenticated access redirects to /login
  - Login succeeds / fails
  - Deposit succeeds / fails
  - Withdrawal succeeds / fails / insufficient funds
  - Logout clears the session
  - Custom error pages
"""


# ── Helper ────────────────────────────────────────────────────────────────────

def login(client, username="alice", password="alice123"):
    """POST to /login and follow all redirects."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# ── Unauthenticated access ────────────────────────────────────────────────────

class TestUnauthenticatedAccess:

    def test_root_redirects_to_login(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_dashboard_redirects_to_login(self, client):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_deposit_page_redirects_to_login(self, client):
        response = client.get("/deposit", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_withdraw_page_redirects_to_login(self, client):
        response = client.get("/withdraw", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:

    def test_login_page_renders(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Sign In" in response.data

    def test_successful_login_redirects_to_dashboard(self, client):
        response = client.post(
            "/login",
            data={"username": "alice", "password": "alice123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_successful_login_shows_dashboard(self, client):
        response = login(client)
        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_wrong_password_shows_error(self, client):
        response = client.post(
            "/login",
            data={"username": "alice", "password": "wrongpass"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid" in response.data

    def test_unknown_username_shows_error(self, client):
        response = client.post(
            "/login",
            data={"username": "nobody", "password": "anything"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid" in response.data

    def test_blank_username_shows_error(self, client):
        response = client.post(
            "/login",
            data={"username": "", "password": "alice123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_already_logged_in_redirects_to_dashboard(self, client):
        login(client)
        response = client.get("/login", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:

    def test_logout_clears_session_and_redirects(self, client):
        login(client)
        response = client.post("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_after_logout_dashboard_is_protected(self, client):
        login(client)
        client.post("/logout")
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ── Deposit ───────────────────────────────────────────────────────────────────

class TestDeposit:

    def test_deposit_page_renders(self, client):
        login(client)
        response = client.get("/deposit")
        assert response.status_code == 200
        assert b"Deposit" in response.data

    def test_valid_deposit_redirects_to_dashboard(self, client):
        login(client)
        response = client.post(
            "/deposit",
            data={"amount": "250"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_valid_deposit_shows_success_message(self, client):
        login(client)
        response = client.post(
            "/deposit",
            data={"amount": "250"},
            follow_redirects=True,
        )
        assert b"Successfully deposited" in response.data

    def test_zero_deposit_shows_error(self, client):
        login(client)
        response = client.post(
            "/deposit",
            data={"amount": "0"},
            follow_redirects=True,
        )
        assert b"greater than zero" in response.data.lower()

    def test_non_numeric_deposit_shows_error(self, client):
        login(client)
        response = client.post(
            "/deposit",
            data={"amount": "abc"},
            follow_redirects=True,
        )
        assert b"number" in response.data.lower()


# ── Withdrawal ────────────────────────────────────────────────────────────────

class TestWithdrawal:

    def test_withdraw_page_shows_balance(self, client):
        login(client)
        response = client.get("/withdraw")
        assert response.status_code == 200
        assert b"1000" in response.data

    def test_valid_withdrawal_redirects_to_dashboard(self, client):
        login(client)
        response = client.post(
            "/withdraw",
            data={"amount": "100"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_valid_withdrawal_shows_success_message(self, client):
        login(client)
        response = client.post(
            "/withdraw",
            data={"amount": "100"},
            follow_redirects=True,
        )
        assert b"Successfully withdrew" in response.data

    def test_overdraft_shows_insufficient_funds_error(self, client):
        login(client)
        response = client.post(
            "/withdraw",
            data={"amount": "9999"},
            follow_redirects=True,
        )
        assert b"Insufficient" in response.data

    def test_zero_withdrawal_shows_error(self, client):
        login(client)
        response = client.post(
            "/withdraw",
            data={"amount": "0"},
            follow_redirects=True,
        )
        assert b"greater than zero" in response.data.lower()


# ── Error pages ───────────────────────────────────────────────────────────────

class TestErrorPages:

    def test_404_returns_custom_page(self, client):
        response = client.get("/this-page-does-not-exist")
        assert response.status_code == 404
        assert b"404" in response.data
