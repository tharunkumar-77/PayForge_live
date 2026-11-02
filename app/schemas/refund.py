from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Literal

class RefundCreate(BaseModel):
    payment_intent_id: str = Field(..., description="ID of the payment intent to refund")
    amount: Decimal = Field(..., gt=0, description="Refund amount, must be positive and <= original payment amount")
    is_partial: bool = Field(False, description="Indicates if this is a partial refund")

class RefundResponse(BaseModel):
    id: str
    payment_intent_id: str
    amount: Decimal
    status: Literal["created", "processing", "completed", "failed", "cancelled"]
    is_partial: bool
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True
