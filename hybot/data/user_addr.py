from sqlalchemy import Column, Table
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy_json import NestedMutableJson

from hybot.data.base import Base

__all__ = "UserAddr",


class UserAddr(Base):
    __tablename__ = "user_addr"

    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True)
    addr_id = Column(Integer, ForeignKey("addr.id", ondelete="CASCADE"), primary_key=True, index=True)
    conf = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})
