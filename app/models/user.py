from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.ledger import gen_uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)

    wallet = relationship("Wallet", back_populates="user", uselist=False)