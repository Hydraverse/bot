from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson

from hybot.data.base import Base

__all__ = "UserAddrToken",


class UserAddrToken(Base):
    __tablename__ = "user_addr_token"

    user_id = Column(Integer, ForeignKey("user_addr.user_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_id = Column(Integer, ForeignKey("user_addr.addr_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    tokn_id = Column(Integer, ForeignKey("tokn.tokn_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_change = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)
    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})
