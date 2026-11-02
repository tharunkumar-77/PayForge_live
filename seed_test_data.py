import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])


def new_id() -> str:
    return str(uuid.uuid4())


def seed() -> None:
    with engine.begin() as conn:
        # Ensure System Float account exists for double-entry balancing
        system_account = conn.execute(
            text("SELECT id FROM accounts WHERE name = :name"),
            {"name": "System Float"},
        ).scalar_one_or_none()

        if not system_account:
            system_account = new_id()
            conn.execute(
                text("""
                    INSERT INTO accounts (id, name, type, currency)
                    VALUES (:id, 'System Float', 'ASSET', 'INR')
                """),
                {"id": system_account},
            )

        existing = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "alice.test@payforge.local"},
        ).first()

        if existing:
            # Check if the existing opening seed transaction is missing its offsetting DEBIT
            opening_tx = conn.execute(
                text("SELECT id FROM transactions WHERE idempotency_key = :key"),
                {"key": "payforge-seed-opening-v1"},
            ).scalar_one_or_none()

            if opening_tx:
                net_imbalance = conn.execute(
                    text("""
                        SELECT COALESCE(SUM(
                            CASE
                                WHEN direction = 'CREDIT' THEN amount
                                WHEN direction = 'DEBIT' THEN -amount
                                ELSE 0
                            END
                        ), 0)
                        FROM ledger_entries
                        WHERE transaction_id = :tx
                    """),
                    {"tx": opening_tx},
                ).scalar_one()

                if net_imbalance > 0:
                    conn.execute(
                        text("""
                            INSERT INTO ledger_entries
                                (id, transaction_id, account_id, amount, direction)
                            VALUES (:id, :tx, :sys_acc, :amt, 'DEBIT')
                        """),
                        {
                            "id": new_id(),
                            "tx": opening_tx,
                            "sys_acc": system_account,
                            "amt": int(net_imbalance),
                        },
                    )
                    print(
                        f"Repaired existing opening transaction with offsetting DEBIT of ₹{net_imbalance}."
                    )
                else:
                    print("Test data already exists and is balanced. No changes made.")
            return

        alice_id, bob_id = new_id(), new_id()
        alice_account, bob_account = new_id(), new_id()
        alice_wallet, bob_wallet = new_id(), new_id()
        opening_tx = new_id()

        conn.execute(
            text("""
                INSERT INTO users (id, email, name)
                VALUES
                    (:alice, 'alice.test@payforge.local', 'Alice Test'),
                    (:bob, 'bob.test@payforge.local', 'Bob Test')
            """),
            {"alice": alice_id, "bob": bob_id},
        )

        conn.execute(
            text("""
                INSERT INTO accounts (id, name, type, currency)
                VALUES
                    (:a, 'Alice Test Wallet', 'ASSET', 'INR'),
                    (:b, 'Bob Test Wallet', 'ASSET', 'INR')
            """),
            {"a": alice_account, "b": bob_account},
        )

        conn.execute(
            text("""
                INSERT INTO wallets (id, user_id, account_id)
                VALUES
                    (:wa, :ua, :aa),
                    (:wb, :ub, :ab)
            """),
            {
                "wa": alice_wallet,
                "ua": alice_id,
                "aa": alice_account,
                "wb": bob_wallet,
                "ub": bob_id,
                "ab": bob_account,
            },
        )

        conn.execute(
            text("""
                INSERT INTO transactions (id, idempotency_key, status, description)
                VALUES (:tx, :key, 'POSTED', 'Test account opening balances')
            """),
            {"tx": opening_tx, "key": "payforge-seed-opening-v1"},
        )

        # Balanced double-entry opening entries:
        # 1500 DEBIT from System Float -> 1000 CREDIT to Alice + 500 CREDIT to Bob
        conn.execute(
            text("""
                INSERT INTO ledger_entries
                    (id, transaction_id, account_id, amount, direction)
                VALUES
                    (:e0, :tx, :sys_acc, 1500, 'DEBIT'),
                    (:e1, :tx, :alice, 1000, 'CREDIT'),
                    (:e2, :tx, :bob, 500, 'CREDIT')
            """),
            {
                "e0": new_id(),
                "e1": new_id(),
                "e2": new_id(),
                "tx": opening_tx,
                "sys_acc": system_account,
                "alice": alice_account,
                "bob": bob_account,
            },
        )

        conn.execute(
            text("""
                INSERT INTO audit_logs (id, transaction_id, event, details)
                VALUES (:id, :tx, 'test_data_seeded', 'Created two test wallets')
            """),
            {"id": new_id(), "tx": opening_tx},
        )

        print("Test data created successfully.")
        print("Alice: alice.test@payforge.local | Account:", alice_account)
        print("Bob:   bob.test@payforge.local   | Account:", bob_account)
        print("Alice opening balance: ₹1,000")
        print("Bob opening balance: ₹500")


if __name__ == "__main__":
    try:
        seed()
    finally:
        engine.dispose()