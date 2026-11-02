from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.wallet import (
    BalanceResponse,
    TransactionRequest,
    TransactionResponse,
    TransferRequest,
)
from app.services.ledger import (
    IdempotencyConflictError,
    get_balance,
    post_transaction,
    safe_transfer,
)

router = APIRouter()


def transaction_response(transaction) -> dict:
    return {
        "transaction_id": transaction.id,
        "status": transaction.status.value,
    }


@router.post("/transactions", status_code=201, response_model=TransactionResponse)
def create_transaction(
    payload: TransactionRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        transaction = post_transaction(
            db=db,
            entries=[entry.model_dump() for entry in payload.entries],
            idempotency_key=payload.idempotency_key,
            description=payload.description,
        )
        return transaction_response(transaction)

    except IdempotencyConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Transaction conflicts with an existing database record.",
        ) from exc


@router.post("/transfer", status_code=201, response_model=TransactionResponse)
def create_transfer(
    payload: TransferRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        transaction = safe_transfer(
            db=db,
            from_account_id=payload.from_account_id,
            to_account_id=payload.to_account_id,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
            description=payload.description,
        )
        return transaction_response(transaction)

    except IdempotencyConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Transaction conflicts with an existing database record.",
        ) from exc


@router.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
def read_balance(
    account_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        balance = get_balance(db, account_id)
        return {
            "account_id": account_id,
            "balance": balance,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc