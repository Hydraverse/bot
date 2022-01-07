from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.future import select as future_select

from .base import Base

__all__ = "User",


class User(Base):
    __tablename__ = "user"

    # required in order to access columns with server defaults
    # or SQL expression defaults, after a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}

    user_id = Column(Integer, unique=True, primary_key=True, autoincrement=True, index=True, nullable=False)

    tgid = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)

    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})

    addrs = relationship("Addr", secondary="user_addr", back_populates="users", cascade="all, delete")
    tokns = relationship("Tokn", secondary="user_tokn", back_populates="users", cascade="all, delete")

    @staticmethod
    def from_tgid(tgid):
        return future_select(lambda: User).where(lambda: User.tgid == tgid)

