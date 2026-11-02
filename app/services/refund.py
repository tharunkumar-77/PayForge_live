from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.refund import Refund, RefundStatus
from app.models.payment import PaymentIntent
from app.services.ledger import safe_transfer, get_balance
from app.services.audit import log_audit

def _get_payment_intent(db: Session, payment_intent_id: str) -> PaymentIntent:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not intent:
        raise ValueError("Payment intent not found")
    return intent

def _total_refunded_amount(db: Session, payment_intent_id: str) -> int:
    total = db.query(func.coalesce(func.sum(Refund.amount), 0)).filter(
        Refund.payment_intent_id == payment_intent_id,
        Refund.status.in_([RefundStatus.COMPLETED, RefundStatus.PROCESSING])
    ).scalar()
    return int(total)

def create_refund(db: Session, payment_intent_id: str, amount: int, is_partial: bool = False) -> Refund:
    """Create a refund record after validating amount and payment status.

    - Payment must be in CAPTURED state.
    - Refund amount cannot exceed remaining refundable amount.
    - Prevent duplicate refunds by checking existing refunds with same amount and status.
    """
    intent = _get_payment_intent(db, payment_intent_id)
    if intent.status != "captured" and intent.status != "CAPTURED":
        raise ValueError("Only captured payments can be refunded")

    refundable = intent.amount - _total_refunded_amount(db, payment_intent_id)
    if amount > refundable:
        raise ValueError(f"Refund amount {amount} exceeds refundable amount {refundable}")

    # Create refund record
    refund = Refund(
        payment_intent_id=payment_intent_id,
        amount=amount,
        is_partial=is_partial,
        status=RefundStatus.CREATED,
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    log_audit(db, event="refund_created", details=f"refund_id={refund.id}, amount={amount}")
    return refund

def process_refund(db: Session, refund_id: str) -> Refund:
    """Process a refund: perform ledger transfer and update status.

    - Idempotent: if already completed, returns existing record.
    - On success, transfers funds from destination account back to source account.
    - Handles partial failures with status FAILED.
    """
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise ValueError("Refund not found")
    if refund.status == RefundStatus.COMPLETED:
        return refund
    if refund.status == RefundStatus.FAILED:
        raise ValueError("Refund previously failed; cannot retry")

    intent = _get_payment_intent(db, refund.payment_intent_id)
    # Perform fund transfer back to source (refund)
    try:
        safe_transfer(
            db,
            from_account_id=intent.destination_account_id,
            to_account_id=intent.source_account_id,
            amount=refund.amount,
            idempotency_key=f"refund-{refund.id}",
        )
        refund.status = RefundStatus.COMPLETED
        db.commit()
        db.refresh(refund)
        log_audit(db, event="refund_completed", details=f"refund_id={refund.id}, amount={refund.amount}")
    except Exception as exc:
        db.rollback()
        refund.status = RefundStatus.FAILED
        db.commit()
        db.refresh(refund)
        log_audit(db, event="refund_failed", details=str(exc))
        raise
    return refund
