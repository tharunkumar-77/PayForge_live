import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime, Enum, CheckConstraint)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AccountType(enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    REVENUE = "revenue"
    EXPENSE = "expense"


class Direction(enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionStatus(enum.Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    REVERSED = "reversed"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)
    type = Column(Enum(AccountType), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    entries = relationship("LedgerEntry", back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    idempotency_key = Column(String, nullable=False, unique=True)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    entries = relationship("LedgerEntry", back_populates="transaction")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("Account", back_populates="entries")
    transaction = relationship("Transaction", back_populates="entries")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),)