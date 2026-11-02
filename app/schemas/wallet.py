from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ledger import Direction


class LedgerEntryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1, max_length=255)
    amount: int = Field(gt=0)
    direction: Direction

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[LedgerEntryRequest] = Field(min_length=2)
    idempotency_key: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_account_id: str = Field(min_length=1, max_length=255)
    to_account_id: str = Field(min_length=1, max_length=255)
    amount: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class TransactionResponse(BaseModel):
    transaction_id: str
    status: str


class BalanceResponse(BaseModel):
    account_id: str
    balance: int