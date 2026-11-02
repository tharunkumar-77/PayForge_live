from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ledger import Account, AccountType
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.user import UserCreateRequest, UserWalletResponse
from app.services.audit import log_audit
from app.services.ledger import get_balance

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=201, response_model=UserWalletResponse)
def create_user(
    payload: UserCreateRequest,
    db: Annotated[Session, Depends(get_db)],
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A user with this email already exists.",
        )

    try:
        user = User(
            name=payload.name.strip(),
            email=payload.email.strip().lower(),
        )
        db.add(user)
        db.flush()

        account = Account(
            name=f"{user.name} Wallet ({user.id[:8]})",
            type=AccountType.ASSET,
            currency=payload.currency.upper(),
        )
        db.add(account)
        db.flush()

        wallet = Wallet(
            user_id=user.id,
            account_id=account.id,
        )
        db.add(wallet)

        log_audit(
            db,
            event="user_wallet_created",
            details=f"user_id={user.id}, account_id={account.id}",
        )

        db.commit()
        db.refresh(user)
        db.refresh(account)
        db.refresh(wallet)

        return {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "wallet_id": wallet.id,
            "account_id": account.id,
            "currency": account.currency,
            "balance": 0,
        }
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="User or wallet conflicts with an existing record.",
        ) from exc


@router.get("/{user_id}", response_model=UserWalletResponse)
def get_user(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.wallet:
        raise HTTPException(status_code=404, detail="User not found.")

    account = db.query(Account).filter(Account.id == user.wallet.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    balance = get_balance(db, account.id)
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "wallet_id": user.wallet.id,
        "account_id": account.id,
        "currency": account.currency,
        "balance": balance,
    }