
"""def do_transfer(idem_key):
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
db.close()"""
import threading
import uuid

from app.database import SessionLocal
from app.models.ledger import Account
from app.services.ledger import get_balance, safe_transfer


def run_same_key_concurrency_test() -> None:
    db = SessionLocal()
    try:
        alice = db.query(Account).filter(Account.name == "Alice Test Wallet").first()
        bob = db.query(Account).filter(Account.name == "Bob Test Wallet").first()
        if not alice or not bob:
            raise RuntimeError(
                "Seed accounts not found. Run `python seed_test_data.py` first."
            )
        alice_id, bob_id = alice.id, bob.id
        before_alice = get_balance(db, alice_id)
        before_bob = get_balance(db, bob_id)
        print("Before — Alice:", before_alice, "Bob:", before_bob)
    finally:
        db.close()

    idem_key = f"same-key-test-{uuid.uuid4().hex[:8]}"
    results: list[str] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def do_transfer() -> None:
        session = SessionLocal()
        try:
            tx = safe_transfer(
                session,
                from_account_id=alice_id,
                to_account_id=bob_id,
                amount=10,
                idempotency_key=idem_key,
            )
            with lock:
                results.append(tx.id)
        except Exception as exc:
            with lock:
                errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=do_transfer) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db = SessionLocal()
    try:
        after_alice = get_balance(db, alice_id)
        after_bob = get_balance(db, bob_id)
        print("After  — Alice:", after_alice, "Bob:", after_bob)
        print(f"Completed: {len(results)} succeeded, {len(errors)} failed")
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(set(results)) == 1, "All threads must return the exact same transaction ID"
        assert after_alice == before_alice - 10, "Alice must be debited only once"
        assert after_bob == before_bob + 10, "Bob must be credited only once"
    finally:
        db.close()


def test_idempotent_concurrent_transfer() -> None:
    run_same_key_concurrency_test()


if __name__ == "__main__":
    run_same_key_concurrency_test()