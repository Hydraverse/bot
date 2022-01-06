from sqlalchemy import Column, Table
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.future import select as future_select

from .base import Base
from .user_addr import UserAddr

__all__ = "User",


class User(Base):
    __tablename__ = "user"

    # required in order to access columns with server defaults
    # or SQL expression defaults, after a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_change = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)
    date_access = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    config = Column(NestedMutableJson, nullable=False, index=True)
    data = Column(NestedMutableJson, nullable=False, index=True)

    tgid = Column(String, nullable=True, unique=True)
    name = Column(String, nullable=True)
    addrs = relationship("Addr", secondary=UserAddr, back_populates="users")

    @staticmethod
    def from_tgid(tgid):
        return future_select(lambda: User).where(lambda: User.tgid == tgid)

