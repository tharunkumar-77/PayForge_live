from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.schemas.refund import RefundCreate, RefundResponse
from app.services.refund import create_refund, process_refund
from app.models.refund import Refund

router = APIRouter(prefix="/refunds", tags=["refunds"])

@router.post("/", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
def create_refund_endpoint(
    payload: RefundCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        refund = create_refund(
            db,
            payment_intent_id=payload.payment_intent_id,
            amount=int(payload.amount),
            is_partial=payload.is_partial,
        )
        return refund
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{refund_id}/process", response_model=RefundResponse)
def process_refund_endpoint(
    refund_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        refund = process_refund(db, refund_id)
        return refund
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Refund processing failed")

@router.get("/{refund_id}", response_model=RefundResponse)
def get_refund(
    refund_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund
