import threading
from app.database import SessionLocal
from app.services.ledger import transfer, get_balance

def do_transfer(idem_key):
    db = SessionLocal()
    try:
        transfer(db, from_account_id="911", to_account_id="912", amount=100, idempotency_key=idem_key)
        print("Success:", idem_key)
    except Exception as e:
        print("Failed:", idem_key, e)
    finally:
        db.close()

db = SessionLocal()
print("Before — 911:", get_balance(db, "911"), "912:", get_balance(db, "912"))
db.close()

threads = []
for i in range(10):
    t = threading.Thread(target=do_transfer, args=(f"concurrent-test-{i}",))
    threads.append(t)

for t in threads:
    t.start()

for t in threads:
    t.join()

db = SessionLocal()
print("After — 911:", get_balance(db, "911"), "912:", get_balance(db, "912"))
db.close()