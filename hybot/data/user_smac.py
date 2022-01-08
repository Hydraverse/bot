from sqlalchemy import Column, ForeignKey, Integer

from hybot.data.base import *

__all__ = "UserSmac",


@dictattrs("user_pk", "smac_pk", "date_create", "date_update", "info", "data")
class UserSmac(DbDateMixin, Base):
    __tablename__ = "user_smac"

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    smac_pk = Column(Integer, ForeignKey("smac.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()
