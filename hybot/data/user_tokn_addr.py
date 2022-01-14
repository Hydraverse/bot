from __future__ import annotations
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *
from .db import DB
from .addr import Addr

__all__ = "UserToknAddr",


class UserToknAddr(DbPkidMixin, Base):
    __tablename__ = "user_tokn_addr"
    __table_args__ = (
        UniqueConstraint("user_addr_pk", "tokn_addr_pk", name="_user_addr_tokn_addr_uc"),
    )

    user_addr_pk = Column(Integer, ForeignKey("user_addr.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)
    tokn_addr_pk = Column(Integer, ForeignKey("tokn_addr.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)

    user_addr = relationship("UserAddr", back_populates="user_addr_tokn_addrs", passive_deletes=True)
    tokn_addr = relationship("ToknAddr", back_populates="tokn_addr_user_addrs", passive_deletes=True)

    def _remove(self, db: DB, user_tokn_addrs):
        tokn_addr = self.tokn_addr
        user_tokn_addrs.remove(self)
        tokn_addr._remove(db, tokn_addr.tokn.tokn_addrs)


Index(UserToknAddr.__tablename__ + "_idx", UserToknAddr.user_addr_pk, UserToknAddr.tokn_addr_pk)
