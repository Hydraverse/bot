from sqlalchemy import Column, ForeignKey, Integer, String

from hybot.data.base import *

__all__ = "UserAddr",


@dictattrs("user_id", "addr_id", "date_create", "date_update", "info", "data")
class UserAddr(DbDateMixin, Base):
    __tablename__ = "user_addr"

    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_id = Column(String(34), ForeignKey("addr.addr_id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()
