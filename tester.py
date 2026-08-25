from app.database import SessionLocal
from app.services.ledger import post_transaction,get_balance
from app.models.ledger import Direction

db = SessionLocal()

# you'll need two real account_ids that exist in your `accounts` table
# for now, insert two rows manually via psql/pgAdmin if you don't have any yet

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

entries = [
    {"account_id": "911", "amount": 300, "direction": Direction.DEBIT},
    {"account_id": "912", "amount": 300, "direction": Direction.CREDIT},
]

txn = post_transaction(db, entries, idempotency_key="manual-test-002", description="manual test transfer")
print("Transaction:", txn.id, txn.status)

print("911 balance:", get_balance(db, "911"))
print("912 balance:", get_balance(db, "912"))