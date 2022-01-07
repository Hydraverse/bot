from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy_json import NestedMutableJson

from hybot.data.base import Base, dictattrs

__all__ = "UserTokn",


@dictattrs("user_id", "addr_id", "date_create", "date_update", "info", "data")
class UserTokn(Base):
    __tablename__ = "user_tokn"
    __mapper_args__ = {"eager_defaults": True}

    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    tokn_id = Column(String(40), ForeignKey("tokn.tokn_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    date_create = Column(DateTime, default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, onupdate=func.now(), index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})
