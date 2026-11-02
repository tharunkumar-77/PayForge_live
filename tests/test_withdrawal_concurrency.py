import threading
import uuid
import time

import pytest
from app.database import SessionLocal
from app.services.ledger import get_balance, safe_transfer
from app.models.ledger import Account, LedgerEntry

# Constants for the test
INITIAL_BALANCE = 10_000
WITHDRAW_AMOUNT = 800
CONCURRENT_REQUESTS = 100

@pytest.fixture(scope="function")
def source_and_sink_accounts():
    """Create a source account with a large balance and a sink account.
    Both accounts are cleaned up after the test.
    """
    # Use existing seeded accounts for source and sink
    db = SessionLocal()
    try:
        # Fetch source (Alice Test Wallet) and sink (Bob Test Wallet) accounts
        source_id = db.query(Account).filter(Account.name == "Alice Test Wallet").first().id
        sink_id = db.query(Account).filter(Account.name == "Bob Test Wallet").first().id
        # Ensure source has sufficient balance by topping up from System Float
        system = db.query(Account).filter(Account.name == "System Float").first()
        if not system:
            raise RuntimeError("System Float account not found in database.")
        # Transfer INITIAL_BALANCE to source if needed
        current_balance = get_balance(db, source_id)
        if current_balance < INITIAL_BALANCE:
            top_up_amount = INITIAL_BALANCE - current_balance
            safe_transfer(
                db,
                from_account_id=system.id,
                to_account_id=source_id,
                amount=top_up_amount,
                idempotency_key=f"topup-{uuid.uuid4().hex[:8]}",
            )
            db.commit()
        yield source_id, sink_id
    finally:
        db.close()

def withdraw_once(from_id, to_id, key):
    db = SessionLocal()
    try:
        safe_transfer(
            db,
            from_account_id=from_id,
            to_account_id=to_id,
            amount=WITHDRAW_AMOUNT,
            idempotency_key=key,
        )
    finally:
        db.close()

def run_concurrent(withdraw_func, *args):
    successes = []
    errors = []
    lock = threading.Lock()
    def worker():
        try:
            withdraw_func(*args)
            with lock:
                successes.append(True)
        except Exception as exc:
            with lock:
                errors.append(exc)
    threads = [threading.Thread(target=worker) for _ in range(CONCURRENT_REQUESTS)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = time.time() - start
    return successes, errors, duration

def test_concurrent_withdrawals(source_and_sink_accounts):
    source_id, sink_id = source_and_sink_accounts
    # Verify initial balance
    db = SessionLocal()
    try:
        assert get_balance(db, source_id) == INITIAL_BALANCE
    finally:
        db.close()
    # Run concurrent withdrawals
    def worker_func():
        key = f"withdraw-{uuid.uuid4().hex[:8]}"
        withdraw_once(source_id, sink_id, key)
    successes, errors, duration = run_concurrent(worker_func)
    # Assertions per requirements
    max_possible = INITIAL_BALANCE // WITHDRAW_AMOUNT
    assert len(successes) <= max_possible, "More withdrawals succeeded than possible"
    assert len(errors) == CONCURRENT_REQUESTS - len(successes), "Unexpected error count"
    # Balance never negative and matches expected
    db = SessionLocal()
    try:
        final_balance = get_balance(db, source_id)
        assert final_balance >= 0
        expected_balance = INITIAL_BALANCE - len(successes) * WITHDRAW_AMOUNT
        assert final_balance == expected_balance
        # Ledger entries for source account should be 2 per successful transaction (debit + credit)
        entry_count = db.query(LedgerEntry).filter(LedgerEntry.account_id == source_id).count()
        assert entry_count == len(successes) * 2
    finally:
        db.close()
    print(f"Concurrent withdrawals: {CONCURRENT_REQUESTS} requests, {len(successes)} succeeded, {len(errors)} failed, duration {duration:.2f}s")
