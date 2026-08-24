from app.database import Base,SessionLocal

from app.models.ledger import Transaction,TransactionStatus,Direction,LedgerEntry,AccountType,Account


def post_transaction(db,entries,idempotency_key,description=None):
    total_credits=sum(e["amount"] for e in entries if e["direction"]==Direction.CREDIT)
    total_debits=sum(e["amount"] for e in entries if e["direction"]==Direction.DEBIT)

    if total_debits != total_credits:
        raise ValueError(f"Unbalanced transaction: debits={total_debits}, credits={total_credits}")