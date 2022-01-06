from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import String
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.orm import relationship
from sqlalchemy.future import select as future_select

from .base import Base
from .user_addr import UserAddr

__all__ = "Addr",


class Addr(Base):
    __tablename__ = "addr"

    # required in order to access columns with server defaults
    # or SQL expression defaults, after a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}

    id = Column(String, primary_key=True, index=True)
    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_change = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)
    date_access = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    config = Column(NestedMutableJson, nullable=False, index=True)
    data = Column(NestedMutableJson, nullable=False, index=True)
    users = relationship("User", secondary=UserAddr, back_populates="users")

    @staticmethod
    def from_user(user):
        return future_select(lambda: Addr).where(lambda: user in Addr.users)
