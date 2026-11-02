from pydantic import BaseModel, ConfigDict, Field


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    currency: str = Field(default="INR", min_length=3, max_length=3)


class UserWalletResponse(BaseModel):
    user_id: str
    name: str
    email: str
    wallet_id: str
    account_id: str
    currency: str
    balance: int