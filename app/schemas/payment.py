from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class PaymentCreate(BaseModel):
    amount: int = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    source_account_id: str
    destination_account_id: str
    description: Optional[str] = None
    idempotency_key: Optional[str] = None

class PaymentResponse(BaseModel):
    id: str
    amount: int
    currency: str
    description: Optional[str]
    status: str
    source_account_id: str
    destination_account_id: str
    idempotency_key: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True
