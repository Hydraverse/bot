from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *
from .db import DB
from .tokn_addr import ToknAddr

__all__ = "UserAddr",


class UserAddr(Base):
    __tablename__ = "user_addr"
    __table_args__ = (
        UniqueConstraint("user_pk", "addr_pk", name="_user_addr_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    user = relationship("User", back_populates="user_addrs", passive_deletes=True)
    addr = relationship("Addr", back_populates="user_addrs", passive_deletes=True)

    def asdict(self):
        return {
            "user": self.user.asdict(),
            "addr": self.addr.asdict(),
        }

    def _remove(self, db: DB, user_addrs):
        addr = self.addr
        user_addrs.remove(self)
        addr._removed_user(db)

    def get_tokn_addr(self, db: DB, tokn, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, tokn, self.addr, create=create)

    def get_addr_tokn(self, db: DB, addr, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, self.addr, addr, create=create)


Index(UserAddr.__tablename__ + "_idx", UserAddr.user_pk, UserAddr.addr_pk)
