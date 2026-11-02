from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ledger import (
    Account,
    Direction,
    LedgerEntry,
    Transaction,
    TransactionStatus,
)
from app.services.audit import log_audit


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency_key is reused with different parameters."""


def _validate_amount(amount: int) -> None:
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("Amount must be an integer.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")


def _normalize_direction(value) -> Direction:
    if isinstance(value, Direction):
        return value

    if isinstance(value, str):
        cleaned = value.strip()
        try:
            return Direction(cleaned.lower())
        except ValueError:
            try:
                return Direction[cleaned.upper()]
            except KeyError:
                pass

    raise ValueError("Direction must be 'debit' or 'credit'.")


def _validate_idempotency_key(key: str) -> None:
    if not isinstance(key, str) or not key.strip():
        raise ValueError("idempotency_key is required.")

    if len(key) > 255:
        raise ValueError("idempotency_key must not exceed 255 characters.")


def _lock_accounts(db: Session, account_ids: set[str]) -> None:
    """Legacy helper kept for compatibility – delegates to deterministic lock helper."""
    lock_accounts_for_update(db, account_ids)

def lock_accounts_for_update(db: Session, account_ids: set[str]) -> None:
    """Lock the given account IDs using SELECT … FOR UPDATE in a deterministic order.
    This prevents deadlocks by always acquiring locks in alphabetical order of IDs.
    Raises ValueError if any account ID is missing.
    """
    sorted_ids = sorted(account_ids)
    accounts = (
        db.query(Account)
        .filter(Account.id.in_(sorted_ids))
        .order_by(Account.id)
        .with_for_update()
        .all()
    )
    found_ids = {account.id for account in accounts}
    missing_ids = set(sorted_ids) - found_ids
    if missing_ids:
        raise ValueError(
            f"Unknown account ID(s): {', '.join(sorted(missing_ids))}."
        )


def _verify_transfer_matches_existing(
    existing: Transaction,
    from_account_id: str,
    to_account_id: str,
    amount: int,
) -> None:
    entries = existing.entries
    if len(entries) != 2:
        raise IdempotencyConflictError(
            "Idempotency key already used for a non-transfer transaction."
        )

    debit_entry = next((e for e in entries if e.direction == Direction.DEBIT), None)
    credit_entry = next((e for e in entries if e.direction == Direction.CREDIT), None)

    if (
        debit_entry is None
        or credit_entry is None
        or debit_entry.account_id != from_account_id
        or credit_entry.account_id != to_account_id
        or debit_entry.amount != amount
        or credit_entry.amount != amount
    ):
        raise IdempotencyConflictError(
            "Idempotency key has already been used with different transfer parameters."
        )


def post_transaction(
    db: Session,
    entries: list[dict],
    idempotency_key: str,
    description: str | None = None,
    *,
    _accounts_already_locked: bool = False,
) -> Transaction:
    """
    Post a balanced ledger transaction atomically.

    Every entry must contain account_id, amount, and direction.
    Amounts use the integer unit supported by the current database model.
    """
    _validate_idempotency_key(idempotency_key)

    if not isinstance(entries, list) or len(entries) < 2:
        raise ValueError("A transaction requires at least two entries.")

    normalized_entries = []
    account_ids: set[str] = set()
    total_debits = 0
    total_credits = 0

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each entry must be an object.")

        account_id = entry.get("account_id")
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("Every entry requires an account_id.")

        amount = entry.get("amount")
        _validate_amount(amount)
        direction = _normalize_direction(entry.get("direction"))

        normalized_entries.append(
            {
                "account_id": account_id,
                "amount": amount,
                "direction": direction,
            }
        )
        account_ids.add(account_id)

        if direction == Direction.DEBIT:
            total_debits += amount
        else:
            total_credits += amount

    if total_debits != total_credits:
        raise ValueError(
            f"Unbalanced transaction: debits={total_debits}, "
            f"credits={total_credits}."
        )

    if not _accounts_already_locked:
        _lock_accounts(db, account_ids)

    existing = (
        db.query(Transaction)
        .filter(Transaction.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        raise IdempotencyConflictError(
            "This idempotency key has already been used. "
            "Use a new key for a new transaction."
        )

    try:
        transaction = Transaction(
            idempotency_key=idempotency_key,
            status=TransactionStatus.POSTED,
            description=description,
        )
        db.add(transaction)
        db.flush()

        for item in normalized_entries:
            db.add(
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=item["account_id"],
                    amount=item["amount"],
                    direction=item["direction"],
                )
            )

        log_audit(
            db,
            event="transaction_posted",
            transaction_id=transaction.id,
            details=f"{len(normalized_entries)} ledger entries",
        )

        db.commit()
        db.refresh(transaction)
        return transaction

    except Exception:
        db.rollback()
        raise


def get_balance(db: Session, account_id: str) -> int:
    account_exists = (
        db.query(Account.id).filter(Account.id == account_id).first()
    )
    if account_exists is None:
        raise ValueError(f"Unknown account ID: {account_id}.")

    balance = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == Direction.CREDIT, LedgerEntry.amount),
                        (LedgerEntry.direction == Direction.DEBIT, -LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            )
        )
        .join(Transaction, Transaction.id == LedgerEntry.transaction_id)
        .filter(
            LedgerEntry.account_id == account_id,
            Transaction.status == TransactionStatus.POSTED,
        )
        .scalar()
    )

    return int(balance)


def transfer(
    db: Session,
    from_account_id: str,
    to_account_id: str,
    amount: int,
    idempotency_key: str,
    description: str | None = None,
) -> Transaction:
    _validate_amount(amount)
    _validate_idempotency_key(idempotency_key)

    if not from_account_id or not to_account_id:
        raise ValueError("Both account IDs are required.")

    if from_account_id == to_account_id:
        raise ValueError("Source and destination accounts must differ.")

    # Lock both accounts in deterministic order before reading balance.
    lock_accounts_for_update(db, {from_account_id, to_account_id})

    current_balance = get_balance(db, from_account_id)

    if current_balance < amount:
        raise ValueError(
            f"Insufficient balance: has {current_balance}, needs {amount}."
        )

    entries = [
        {
            "account_id": from_account_id,
            "amount": amount,
            "direction": Direction.DEBIT,
        },
        {
            "account_id": to_account_id,
            "amount": amount,
            "direction": Direction.CREDIT,
        },
    ]

    return post_transaction(
        db=db,
        entries=entries,
        idempotency_key=idempotency_key,
        description=description,
        _accounts_already_locked=True,
    )


def safe_transfer(
    db: Session,
    from_account_id: str,
    to_account_id: str,
    amount: int,
    idempotency_key: str,
    description: str | None = None,
) -> Transaction:
    """
    Return the existing transaction for a previously used key if parameters match.
    Concurrent duplicate submissions are handled safely via unique constraint.
    """
    _validate_amount(amount)
    _validate_idempotency_key(idempotency_key)

    if not from_account_id or not to_account_id:
        raise ValueError("Both account IDs are required.")

    if from_account_id == to_account_id:
        raise ValueError("Source and destination accounts must differ.")

    # Validate that both accounts exist and have the same currency
    from_account = db.query(Account).filter(Account.id == from_account_id).first()
    to_account = db.query(Account).filter(Account.id == to_account_id).first()
    if from_account is None:
        raise ValueError(f"Unknown source account: {from_account_id}.")
    if to_account is None:
        raise ValueError(f"Unknown destination account: {to_account_id}.")
    if from_account.currency != to_account.currency:
        raise ValueError("Source and destination accounts must use the same currency.")

    existing = (
        db.query(Transaction)
        .filter(Transaction.idempotency_key == idempotency_key)
        .first()
    )

    if existing:
        _verify_transfer_matches_existing(
            existing, from_account_id, to_account_id, amount
        )
        return existing

    try:
        return transfer(
            db=db,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            idempotency_key=idempotency_key,
            description=description,
        )
    except (IntegrityError, IdempotencyConflictError):
        db.rollback()

        existing = (
            db.query(Transaction)
            .filter(Transaction.idempotency_key == idempotency_key)
            .first()
        )

        if existing:
            _verify_transfer_matches_existing(
                existing, from_account_id, to_account_id, amount
            )
            return existing

        raise