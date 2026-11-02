from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.payment import PaymentIntent, PaymentStatus
from app.schemas.payment import PaymentCreate
from app.services.ledger import get_balance, safe_transfer


def _get_intent(db: Session, payment_id: str) -> PaymentIntent:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    return intent


def _validate_transition(current_status: PaymentStatus, allowed: set[PaymentStatus]):
    if current_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid state transition from {current_status.value}",
        )


def create_payment_intent(db: Session, payload: PaymentCreate) -> PaymentIntent:
    # Ensure source and destination accounts exist via foreign key constraints
    intent = PaymentIntent(
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        source_account_id=payload.source_account_id,
        destination_account_id=payload.destination_account_id,
        idempotency_key=payload.idempotency_key,
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    return intent


def authorize_payment(db: Session, payment_id: str) -> PaymentIntent:
    intent = _get_intent(db, payment_id)
    _validate_transition(intent.status, {PaymentStatus.CREATED})
    # Verify sufficient balance on source account
    balance = get_balance(db, intent.source_account_id)
    if balance < intent.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds for authorization")
    intent.status = PaymentStatus.AUTHORIZED
    db.commit()
    db.refresh(intent)
    return intent


def capture_payment(db: Session, payment_id: str) -> PaymentIntent:
    intent = _get_intent(db, payment_id)
    _validate_transition(intent.status, {PaymentStatus.AUTHORIZED})
    # Perform actual fund transfer using existing safe_transfer
    safe_transfer(
        db,
        from_account_id=intent.source_account_id,
        to_account_id=intent.destination_account_id,
        amount=intent.amount,
        idempotency_key=f"capture-{intent.id}",
    )
    db.commit()
    intent.status = PaymentStatus.CAPTURED
    db.commit()
    db.refresh(intent)
    return intent


def fail_payment(db: Session, payment_id: str) -> PaymentIntent:
    intent = _get_intent(db, payment_id)
    _validate_transition(intent.status, {PaymentStatus.CREATED, PaymentStatus.AUTHORIZED})
    intent.status = PaymentStatus.FAILED
    db.commit()
    db.refresh(intent)
    return intent


def cancel_payment(db: Session, payment_id: str) -> PaymentIntent:
    intent = _get_intent(db, payment_id)
    _validate_transition(intent.status, {PaymentStatus.CREATED})
    intent.status = PaymentStatus.CANCELLED
    db.commit()
    db.refresh(intent)
    return intent
