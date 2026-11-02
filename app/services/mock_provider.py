import random
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.models.payment import PaymentIntent, PaymentStatus
from app.models.provider import ProviderResponse, ProviderResponseStatus
from app.services.payment import _get_intent, _validate_transition
from app.services.ledger import safe_transfer

# Configuration for mock behavior
# In a real scenario this could be driven by env vars or test parameters
MOCK_BEHAVIOR = {
    "success_rate": 0.7,   # 70% chance of success
    "decline_rate": 0.15,  # 15% chance of decline
    "timeout_rate": 0.10,  # 10% chance of timeout (retryable)
    "error_rate": 0.05,    # 5% chance of provider error (non‑retryable)
}

def _choose_status() -> ProviderResponseStatus:
    r = random.random()
    if r < MOCK_BEHAVIOR["success_rate"]:
        return ProviderResponseStatus.SUCCESS
    r -= MOCK_BEHAVIOR["success_rate"]
    if r < MOCK_BEHAVIOR["decline_rate"]:
        return ProviderResponseStatus.DECLINED
    r -= MOCK_BEHAVIOR["decline_rate"]
    if r < MOCK_BEHAVIOR["timeout_rate"]:
        return ProviderResponseStatus.TIMEOUT
    return ProviderResponseStatus.ERROR

def _record_response(db: Session, intent_id: str, status: ProviderResponseStatus, data: Optional[str] = None) -> ProviderResponse:
    response = ProviderResponse(
        payment_intent_id=intent_id,
        status=status,
        response_data=data,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return response

def process_payment(db: Session, payment_id: str, max_retries: int = 3) -> ProviderResponse:
    """Simulate an external payment provider.

    - Handles duplicate calls by returning the existing ProviderResponse.
    - Retries on TIMEOUT up to ``max_retries``.
    - On SUCCESS performs the actual ledger transfer and updates the intent status to CAPTURED.
    - On DECLINED or ERROR marks the intent as FAILED.
    """
    intent = _get_intent(db, payment_id)
    # Prevent duplicate processing
    existing = (
        db.query(ProviderResponse)
        .filter(ProviderResponse.payment_intent_id == payment_id)
        .first()
    )
    if existing:
        return existing

    attempt = 0
    while attempt <= max_retries:
        status = _choose_status()
        if status == ProviderResponseStatus.TIMEOUT:
            attempt += 1
            if attempt > max_retries:
                # Exhausted retries – treat as error
                status = ProviderResponseStatus.ERROR
            else:
                # Simple back‑off before retrying
                time.sleep(0.2 * attempt)
                continue
        # Record the provider response
        response = _record_response(db, payment_id, status, data="mocked response")

        if status == ProviderResponseStatus.SUCCESS:
            # Perform actual fund transfer
            safe_transfer(
                db,
                from_account_id=intent.source_account_id,
                to_account_id=intent.destination_account_id,
                amount=intent.amount,
                idempotency_key=f"capture-{intent.id}",
            )
            intent.status = PaymentStatus.CAPTURED
            db.commit()
            db.refresh(intent)
        else:
            # Declined or error – mark intent as FAILED
            intent.status = PaymentStatus.FAILED
            db.commit()
            db.refresh(intent)
        return response
    # Should never reach here
    raise RuntimeError("Unexpected flow in mock provider processing")
