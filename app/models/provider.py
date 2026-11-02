import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ProviderResponseStatus(enum.Enum):
    SUCCESS = "success"
    DECLINED = "declined"
    TIMEOUT = "timeout"
    ERROR = "error"


class ProviderResponse(Base):
    __tablename__ = "provider_responses"

    id = Column(String, primary_key=True, default=gen_uuid)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False)
    status = Column(Enum(ProviderResponseStatus), nullable=False)
    response_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment_intent = relationship("PaymentIntent", backref="provider_responses")

    __table_args__ = (
        # Ensure one response per intent for idempotency
        # (optional) Index could be added here
    )
