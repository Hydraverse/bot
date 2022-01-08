from sqlalchemy import Column, ForeignKey, Integer

from hybot.data.base import *

__all__ = "UserTokn",


@dictattrs("user_pk", "tokn_pk", "date_create", "date_update", "info", "data")
class UserTokn(DbDateMixin, Base):
    __tablename__ = "user_tokn"

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    tokn_pk = Column(Integer, ForeignKey("tokn.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()
