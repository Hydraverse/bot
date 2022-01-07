from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import func
from sqlalchemy_json import NestedMutableJson
from datetime import datetime

from hybot.data.base import Base

__all__ = "UserAddr",


class UserAddr(Base):
    __tablename__ = "user_addr"

    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_id = Column(Integer, ForeignKey("addr.addr_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, server_default=func.now(), onupdate=datetime.now, nullable=False, index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})
