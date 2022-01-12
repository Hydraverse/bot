from __future__ import annotations
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *

__all__ = "UserAddr",


@dictattrs("pkid", "user_pk", "addr_pk", "date_create", "date_update", "info", "data", "user", "addr")
class UserAddr(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "user_addr"
    __table_args__ = (
        UniqueConstraint("user_pk", "addr_pk", name="_user_addr_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()

    user = relationship("User", back_populates="user_addrs", passive_deletes=True)
    addr = relationship("Addr", back_populates="user_addrs", passive_deletes=True)

    user_addr_txes = relationship(
        "UserAddrTX",
        back_populates="user_addr",
        cascade="all, delete-orphan",
        single_parent=True
    )

    def _removed_user(self, db):
        # self.user.user_addrs.remove(self)

        for user_addr_tx in self.user_addr_txes:
            user_addr_tx._removed(db)

        self.user_addr_txes.clear()
        self.addr._removed(db, self)


Index(UserAddr.__tablename__ + "_idx", UserAddr.user_pk, UserAddr.addr_pk)
