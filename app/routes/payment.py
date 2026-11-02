from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID

from app.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment import (
    create_payment_intent,
    authorize_payment,
    capture_payment,
    fail_payment,
    cancel_payment,
)

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/", response_model=PaymentResponse, status_code=201)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db), user = Depends(get_current_user)):
    intent = create_payment_intent(db, payload)
    return intent

@router.post("/{payment_id}/authorize", response_model=PaymentResponse)
def authorize(payment_id: UUID, db=Depends(get_db)):
    intent = authorize_payment(db, str(payment_id))
    return intent

@router.post("/{payment_id}/capture", response_model=PaymentResponse)
def capture(payment_id: UUID, db=Depends(get_db)):
    intent = capture_payment(db, str(payment_id))
    return intent

@router.post("/{payment_id}/fail", response_model=PaymentResponse)
def fail(payment_id: UUID, db=Depends(get_db)):
    intent = fail_payment(db, str(payment_id))
    return intent

@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
def cancel(payment_id: UUID, db=Depends(get_db)):
    intent = cancel_payment(db, str(payment_id))
    return intent
