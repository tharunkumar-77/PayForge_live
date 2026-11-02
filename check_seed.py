
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

try:
    with engine.connect() as conn:
        for email in (
            "alice.test@payforge.local",
            "bob.test@payforge.local",
        ):
            user = conn.execute(
                text("SELECT id, name FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()

            if not user:
                print(f"{email}: NOT FOUND")
                continue

            print(f"\n{user.name} ({user.id})")

            rows = conn.execute(text("""
                SELECT a.id, a.name,
                       COALESCE(SUM(
                           CASE
                               WHEN le.direction = 'CREDIT' THEN le.amount
                               WHEN le.direction = 'DEBIT' THEN -le.amount
                               ELSE 0
                           END
                       ), 0) AS balance
                FROM wallets w
                JOIN accounts a ON a.id = w.account_id
                LEFT JOIN ledger_entries le ON le.account_id = a.id
                WHERE w.user_id = :uid
                GROUP BY a.id, a.name
            """), {"uid": user.id}).fetchall()

            for row in rows:
                print(
                    f"  Account: {row.name} | ID: {row.id} "
                    f"| Balance: {row.balance}"
                )

        totals = conn.execute(text("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN direction = 'DEBIT' THEN amount
                    WHEN direction = 'CREDIT' THEN -amount
                    ELSE 0
                END
            ), 0)
            FROM ledger_entries
        """)).scalar_one()

        print(f"\nLedger debit-minus-credit total: {totals}")

finally:
    engine.dispose()
