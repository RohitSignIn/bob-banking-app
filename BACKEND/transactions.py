"""
transactions.py
---------------
Business logic for deposit and withdrawal operations.

These functions are deliberately free of Flask / HTTP concepts.
They receive plain Python values, apply business rules, interact with the
database layer, and return a TransactionResult so the calling route handler
can decide what response to send.
"""

from database import (
    get_account_by_customer_id,
    update_account_balance,
    insert_transaction,
)
from models import TransactionResult

# Maximum single-transaction amount (reasonable guard against input errors)
MAX_TRANSACTION_AMOUNT = 1_000_000.00


# ---------------------------------------------------------------------------
# Input validation helper (shared by deposit and withdrawal)
# ---------------------------------------------------------------------------

def _validate_amount(raw_amount: str) -> tuple[bool, str, float]:
    """
    Parse and validate a raw string amount from a form submission.

    Returns a tuple: (is_valid, error_message, parsed_float)
    If is_valid is False the float will be 0.0.
    """
    if not raw_amount or not str(raw_amount).strip():
        return False, "Please enter an amount.", 0.0

    try:
        amount = float(str(raw_amount).strip())
    except ValueError:
        return False, "Amount must be a valid number.", 0.0

    if amount <= 0:
        return False, "Amount must be greater than zero.", 0.0

    if amount > MAX_TRANSACTION_AMOUNT:
        return (
            False,
            f"Amount exceeds the maximum allowed transaction of "
            f"£{MAX_TRANSACTION_AMOUNT:,.2f}.",
            0.0,
        )

    return True, "", round(amount, 2)


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------

def process_deposit(customer_id: int, raw_amount: str) -> TransactionResult:
    """
    Deposit *raw_amount* into the account belonging to *customer_id*.

    Steps:
      1. Validate the amount string.
      2. Load the account from the database.
      3. Add the amount to the current balance.
      4. Persist the new balance.
      5. Record the transaction.
      6. Return success with the new balance.
    """
    # Step 1 — validate input
    is_valid, error_msg, amount = _validate_amount(raw_amount)
    if not is_valid:
        return TransactionResult(success=False, message=error_msg)

    # Step 2 — load account
    account = get_account_by_customer_id(customer_id)
    if account is None:
        return TransactionResult(
            success=False,
            message="Account not found. Please contact support.",
        )

    # Step 3 — compute new balance
    new_balance = round(account["balance"] + amount, 2)

    # Step 4 — persist balance (atomic: both writes in the same db transaction
    #           are handled by database.py using db.commit() after each call;
    #           for a workshop scenario this is acceptable)
    update_account_balance(account["id"], new_balance)

    # Step 5 — record the event
    insert_transaction(account["id"], "deposit", amount)

    return TransactionResult(
        success=True,
        message=f"Successfully deposited £{amount:,.2f}. New balance: £{new_balance:,.2f}.",
        data={"new_balance": new_balance},
    )


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------

def process_withdrawal(customer_id: int, raw_amount: str) -> TransactionResult:
    """
    Withdraw *raw_amount* from the account belonging to *customer_id*.

    Steps:
      1. Validate the amount string.
      2. Load the account from the database.
      3. Check that the balance covers the withdrawal.
      4. Subtract the amount from the current balance.
      5. Persist the new balance.
      6. Record the transaction.
      7. Return success with the new balance.
    """
    # Step 1 — validate input
    is_valid, error_msg, amount = _validate_amount(raw_amount)
    if not is_valid:
        return TransactionResult(success=False, message=error_msg)

    # Step 2 — load account
    account = get_account_by_customer_id(customer_id)
    if account is None:
        return TransactionResult(
            success=False,
            message="Account not found. Please contact support.",
        )

    current_balance = account["balance"]

    # Step 3 — check sufficient funds
    if amount > current_balance:
        return TransactionResult(
            success=False,
            message=(
                f"Insufficient funds. "
                f"You requested £{amount:,.2f} but your balance is £{current_balance:,.2f}."
            ),
        )

    # Step 4 — compute new balance
    new_balance = round(current_balance - amount, 2)

    # Step 5 — persist balance
    update_account_balance(account["id"], new_balance)

    # Step 6 — record the event
    insert_transaction(account["id"], "withdrawal", amount)

    return TransactionResult(
        success=True,
        message=f"Successfully withdrew £{amount:,.2f}. New balance: £{new_balance:,.2f}.",
        data={"new_balance": new_balance},
    )
