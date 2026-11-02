import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("postgresql+psycopg://postgres:PayForgeDev2026!@localhost:5432/payment_gateway")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing from .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        tables = connection.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        ).scalars().all()

        print(f"Connected to database: {database}")
        print("\nExisting tables:")

        if tables:
            for table in tables:
                print(f"- {table}")
        else:
            print("No tables found.")

except Exception as error:
    print(f"Database check failed: {error}")

finally:
    engine.dispose()