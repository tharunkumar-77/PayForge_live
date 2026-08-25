from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ledger import post_transaction, get_balance

router = APIRouter()


@router.post("/transactions")
def create_transactions(payload: dict, db: Session = Depends(get_db)):
    try:
        entries = payload["entries"]
        idempotency_key = payload["idempotency_key"]
        description = payload.get("description")

        txn = post_transaction(db, entries, idempotency_key, description)
        return {"transaction_id": txn.id, "status": txn.status.value}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/{account_id}/balance")
def read_balance(account_id: str, db: Session = Depends(get_db)):
    balance = get_balance(db, account_id)
    return {"account_id": account_id, "balance": balance}