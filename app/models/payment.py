import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, CheckConstraint, Index
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.ledger import Account


def gen_uuid():
    return str(uuid.uuid4())


class PaymentStatus(enum.Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String, primary_key=True, default=gen_uuid)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    description = Column(String, nullable=True)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.CREATED)
    source_account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    destination_account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    idempotency_key = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    source_account = relationship("Account", foreign_keys=[source_account_id])
    destination_account = relationship("Account", foreign_keys=[destination_account_id])
    refunds = relationship("Refund", back_populates="payment_intent", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        CheckConstraint("char_length(currency) = 3", name="ck_payment_currency_length"),
        Index("ix_payment_intent_idempotency_key", "idempotency_key"),
    )
