from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import func
from sqlalchemy_json import NestedMutableJson
from datetime import datetime

from hybot.data.base import Base

__all__ = "UserTokn",


class UserTokn(Base):
    __tablename__ = "user_tokn"

    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    tokn_id = Column(Integer, ForeignKey("tokn.tokn_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)

    conf = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})
