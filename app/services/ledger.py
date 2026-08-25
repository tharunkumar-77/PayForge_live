from app.database import Base,SessionLocal

from app.models.ledger import Transaction,TransactionStatus,Direction,LedgerEntry,AccountType,Account


def post_transaction(db,entries,idempotency_key,description=None):
    total_credits=sum(e["amount"] for e in entries if e["direction"]==Direction.CREDIT)
    total_debits=sum(e["amount"] for e in entries if e["direction"]==Direction.DEBIT)

    if total_debits != total_credits:
        raise ValueError(f"Unbalanced transaction: debits={total_debits}, credits={total_credits}")

    transaction=Transaction(idempotency_key=idempotency_key,status=TransactionStatus.POSTED,description=description)

    ledger = []
    for e in entries:
        ledger_entry = LedgerEntry(
            account_id=e["account_id"],
            amount=e["amount"],
            direction=e["direction"]
        )
        ledger.append(ledger_entry)

    db.add(transaction)
    db.flush()

    for entry in ledger:
        entry.transaction_id=transaction.id
        db.add(entry)

    db.commit()
    db.refresh(transaction)

    return transaction


def get_balance(db,account_id):
    entries=db.query(LedgerEntry).filter(LedgerEntry.account_id==account_id).all()

    total_credits=sum(e.amount for e in entries if e.direction==Direction.CREDIT)
    total_debits=sum(e.amount for e in entries if e.direction==Direction.DEBIT)

    balance=total_credits-total_debits
    return balance