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


@dictattrs("user")
class UserAddr(Base):
    __tablename__ = "user_addr"
    __table_args__ = (
        UniqueConstraint("user_pk", "addr_pk", name="_user_addr_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    user = relationship("User", back_populates="user_addrs", passive_deletes=True)

    addr = relationship("Addr", back_populates="addr_users", foreign_keys=(addr_pk,), passive_deletes=True)

    tokn = relationship(
        "Tokn",
        viewonly=True,
        primaryjoin="""and_(
            Tokn.pkid == UserAddr.addr_pk,
        )""",
        foreign_keys=(addr_pk,)
    )

    def asdict(self) -> AttrDict:
        d = super(UserAddr, self).asdict()

        if self.addr.addr_tp == Addr.Type.T:
            d.tokn = self.tokn.asdict()
        else:
            d.addr = self.addr.asdict()

        return d

    def _remove(self, db: DB, user_addrs):
        addr = self.addr
        user_addrs.remove(self)
        addr._removed_user(db)

    def get_tokn_addr(self, db: DB, tokn: Tokn, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, tokn, self.addr, create=create)

    def get_addr_tokn(self, db: DB, addr: Addr, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, self.tokn, addr, create=create)


Index(UserAddr.__tablename__ + "_idx", UserAddr.user_pk, UserAddr.addr_pk)
