
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

try:
    with engine.connect() as conn:
        print("=== Ledger entries by direction ===")
        rows = conn.execute(text("""
            SELECT direction, COUNT(*) AS entries, SUM(amount) AS total
            FROM ledger_entries
            GROUP BY direction
            ORDER BY direction
        """)).fetchall()

        for row in rows:
            print(f"{row.direction}: count={row.entries}, total={row.total}")

        print("\n=== Entries grouped by transaction ===")
        rows = conn.execute(text("""
            SELECT t.id, t.idempotency_key, t.description,
                   le.direction, SUM(le.amount) AS total
            FROM transactions t
            JOIN ledger_entries le ON le.transaction_id = t.id
            GROUP BY t.id, t.idempotency_key, t.description, le.direction
            ORDER BY t.created_at
        """)).fetchall()

        for row in rows:
            print(
                f"Transaction={row.id} | Key={row.idempotency_key} | "
                f"Description={row.description} | "
                f"{row.direction}={row.total}"
            )

finally:
    engine.dispose()
