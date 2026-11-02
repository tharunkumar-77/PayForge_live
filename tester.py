
"""entries = [
    {"account_id": "911", "amount": 300, "direction": Direction.DEBIT},
    {"account_id": "912", "amount": 300, "direction": Direction.CREDIT},  
]

txn = post_transaction(db, entries, idempotency_key="test-002", description="unbalanced test")
print("Success:", txn.id, txn.status)
"""


"""from app.services.ledger import get_balance

bal_1=get_balance(db,"911")
bal_2=get_balance(db,"912")


print("Account 911 balance:", bal_1)
print("Account 912 balance:", bal_2)
"""


db = SessionLocal()


"""entries = [

    {"account_id": "911", "amount": 300, "direction": Direction.DEBIT},
    {"account_id": "912", "amount": 300, "direction": Direction.CREDIT},
]

txn = post_transaction(db, entries, idempotency_key="manual-test-002", description="manual test transfer")
print("Transaction:", txn.id, txn.status)

print("911 balance:", get_balance(db, "911"))
print("912 balance:", get_balance(db, "912"))"""

import uuid

from app.database import SessionLocal
from app.models.ledger import Account
from app.services.ledger import get_balance, safe_transfer


def main() -> None:
    db = SessionLocal()
    try:
        alice = db.query(Account).filter(Account.name == "Alice Test Wallet").first()
        bob = db.query(Account).filter(Account.name == "Bob Test Wallet").first()

        if not alice or not bob:
            raise RuntimeError(
                "Seed accounts not found. Run `python seed_test_data.py` first."
            )

        print(
            "Before — Alice:",
            get_balance(db, alice.id),
            "Bob:",
            get_balance(db, bob.id),
        )

        idem_key = f"transfer-test-{uuid.uuid4().hex[:8]}"
        txn = safe_transfer(
            db,
            from_account_id=alice.id,
            to_account_id=bob.id,
            amount=100,
            idempotency_key=idem_key,
            description="Tester script transfer",
        )
        print("Transfer:", txn.id, txn.status.value)

        print(
            "After  — Alice:",
            get_balance(db, alice.id),
            "Bob:",
            get_balance(db, bob.id),
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()










