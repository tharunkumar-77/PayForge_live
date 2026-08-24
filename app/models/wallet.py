from sqlalchemy import Column,String,Integer,ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.ledger import gen_uuid

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False, unique=True)

    user = relationship("User", back_populates="wallet")
    account = relationship("Account")