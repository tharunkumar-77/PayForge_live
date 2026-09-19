from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker,declarative_base

db_url="postgresql://postgres:1234@localhost:5432/payment_gateway"

engine=create_engine(db_url)
sessionlocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)
base=declarative_base()

def get_db():
    db=sessionlocal()

    try:
        yield db

    finally:
        db.close()

