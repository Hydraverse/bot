from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import func
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base

__all__ = "Addr",


class Addr(Base):
    __tablename__ = "addr"

    # required in order to access columns with server defaults
    # or SQL expression defaults, after a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}

    addr_id = Column(Integer, unique=True, primary_key=True, autoincrement=True, index=True, nullable=False)
    address = Column(String, nullable=False, unique=True, index=True)

    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})

    users = relationship("User", secondary="user_addr", back_populates="addrs", passive_deletes=True)
