from __future__ import annotations
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *
from .db import DB
from .user_tokn_addr import UserToknAddr
from .addr import Addr

__all__ = "UserAddr", "UserToknAddr"


class UserAddr(DbPkidMixin, Base):
    __tablename__ = "user_addr"
    __table_args__ = (
        UniqueConstraint("user_pk", "addr_pk", name="_user_addr_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)

    user = relationship("User", back_populates="user_addrs", passive_deletes=True)
    addr = relationship("Addr", back_populates="user_addrs", passive_deletes=True)

    user_addr_tokn_addrs = relationship(
        UserToknAddr,
        back_populates="user_addr",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    def _remove(self, db: DB, user_addrs):
        addr = self.addr

        for user_addr_tokn_addr in list(self.user_addr_tokn_addrs):
            user_addr_tokn_addr._remove(db, self.user_addr_tokn_addrs)

        user_addrs.remove(self)
        addr._removed_user(db)


Index(UserAddr.__tablename__ + "_idx", UserAddr.user_pk, UserAddr.addr_pk)
