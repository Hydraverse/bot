from __future__ import annotations

from typing import List

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, or_, event
from sqlalchemy.orm import relationship

from .base import *
from .addr import Addr
from .user_addr import UserAddr

__all__ = "UserAddrTX",


@dictattrs("tx_pk", "user_addr_pk")
class UserAddrTX(Base):
    __tablename__ = "user_addr_tx"
    __table_args__ = (
        UniqueConstraint("tx_pk", "user_addr_pk", name="_tx_user_addr_uc"),
    )
    __mapper_args__ = {"eager_defaults": True}

    tx_pk = Column(Integer, ForeignKey("tx.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    user_addr_pk = Column(Integer, ForeignKey("user_addr.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)

    tx = relationship("TX", back_populates="user_addr_txes", passive_deletes=True)
    user_addr = relationship("UserAddr", back_populates="user_addr_txes", passive_deletes=True)

    def _removed(self, db):
        self.tx._removed(db, self)

    @staticmethod
    def _load(db, tx) -> bool:
        """Correspond UserAddr's to TX."""

        addresses = set()

        vo_filt = lambda vo: "scriptPubKey" in vo and "addresses" in vo["scriptPubKey"]

        for vout in filter(vo_filt, tx.vouts_out):
            addresses.update(vout["scriptPubKey"]["addresses"])

        for vout in filter(vo_filt, tx.vouts_inp.values()):
            addresses.update(vout["scriptPubKey"]["addresses"])

        user_addrs: List[UserAddr] = db.Session.query(
            UserAddr,
        ).join(
            Addr,
            UserAddr.addr_pk == Addr.pkid
        ).where(
            or_(
                Addr.addr_hy.in_(addresses),
                Addr.addr_hx.in_(addresses),
            )
        ).all()

        added = False

        for user_addr in user_addrs:
            uatx = UserAddrTX(tx=tx, user_addr=user_addr)
            db.Session.add(uatx)
            added |= True

        return added


Index(UserAddrTX.__tablename__ + "_idx", UserAddrTX.user_addr_pk, UserAddrTX.tx_pk)
