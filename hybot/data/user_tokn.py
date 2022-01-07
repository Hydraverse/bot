from sqlalchemy import Column, ForeignKey, Integer, String

from hybot.data.base import *

__all__ = "UserTokn",


@dictattrs("user_id", "tokn_id", "date_create", "date_update", "info", "data")
class UserTokn(DbDateMixin, Base):
    __tablename__ = "user_tokn"

    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    tokn_id = Column(String(40), ForeignKey("tokn.tokn_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()
