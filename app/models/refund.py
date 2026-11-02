import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Enum, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class RefundStatus(str, enum.Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, default=gen_uuid)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum(RefundStatus), default=RefundStatus.CREATED, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_partial = Column(Boolean, default=False)

    payment_intent = relationship("PaymentIntent", back_populates="refunds")
