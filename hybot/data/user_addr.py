from __future__ import annotations

from typing import Optional, List

from attrdict import AttrDict
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *
from .db import DB
from .addr import Addr, Tokn
from .tokn_addr import ToknAddr

__all__ = "UserAddr",


@dictattrs("user", "addr")
class UserAddr(Base):
    __tablename__ = "user_addr"
    __table_args__ = (
        UniqueConstraint("user_pk", "addr_pk", name="_user_addr_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    user = relationship("User", back_populates="user_addrs", passive_deletes=True)
    addr = relationship("Addr", back_populates="addr_users", passive_deletes=True)
    tokn = relationship("Tokn", back_populates="tokn_users", primaryjoin="and_(UserAddr.addr_pk == Addr.pkid, Tokn.pkid == Addr.pkid)")

    # Polymorphic relations
    # smac = relationship("Smac", primaryjoin="Smac.pkid == UserAddr.addr_pk", passive_deletes=True)
    # tokn = relationship("Tokn", primaryjoin="Tokn.pkid == UserAddr.addr_pk", passive_deletes=True)

    # def asdict(self, full=True) -> AttrDict:
    #     attrs = super().asdict()
    #
    #     if not full:
    #         attrs.addr = self.addr.asdict()
    #         return attrs
    #
    #     if self.addr.addr_tp == Addr.Type.T:
    #         attrs.addr = self.tokn.asdict()
    #
    #     elif self.addr.addr_tp == Addr.Type.S:
    #         attrs.addr = self.smac.asdict()
    #
    #     else:
    #         attrs.addr = self.addr.asdict()
    #
    #     return attrs

    def _remove(self, db: DB, user_addrs):
        addr = self.addr
        user_addrs.remove(self)
        addr._removed_user(db)

    def get_tokn_addr(self, db: DB, tokn: Tokn, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, tokn, self.addr, create=create)

    def get_addr_tokn(self, db: DB, addr: Addr, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, self.tokn, addr, create=create)


Index(UserAddr.__tablename__ + "_idx", UserAddr.user_pk, UserAddr.addr_pk)
