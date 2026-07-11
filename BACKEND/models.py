"""
models.py
---------
Lightweight dataclass definitions for the three core entities.
No ORM is used; these classes simply give named structure to data
that is fetched from SQLite rows.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Customer:
    """Represents a registered bank customer."""
    id: int
    username: str
    password_hash: str
    full_name: str


@dataclass
class Account:
    """Represents a customer's bank account and its current balance."""
    id: int
    customer_id: int
    balance: float


@dataclass
class Transaction:
    """Represents a single deposit or withdrawal event."""
    id: int
    account_id: int
    transaction_type: str          # "deposit" or "withdrawal"
    amount: float
    created_at: datetime


@dataclass
class TransactionResult:
    """
    Uniform return type from service-layer functions.
    Keeps route handlers clean: check .success, read .message or .data.
    """
    success: bool
    message: str
    data: Optional[object] = None
