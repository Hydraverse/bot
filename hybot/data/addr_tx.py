from __future__ import annotations

from typing import List

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, or_, event
from sqlalchemy.orm import relationship

from .base import *
from .db import DB
from .tx import TX

__all__ = "AddrTX",


class AddrTX(Base):
    __tablename__ = "addr_tx"
    __table_args__ = (
        UniqueConstraint("addr_pk", "tx_pk", name="_addr_tx_uc"),
    )
    __mapper_args__ = {"eager_defaults": True}

    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    tx_pk = Column(Integer, ForeignKey("tx.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)

    addr = relationship("Addr", back_populates="addr_txes", passive_deletes=True)
    tx = relationship("TX", back_populates="addr_txes", passive_deletes=True)

    def _remove(self, db: DB, addr_txes):
        tx = self.tx
        addr_txes.remove(self)
        tx._removed_addr(db)

    def on_new_tx(self, db: DB):
        self.addr.on_new_tx(db, self)
        db.Session.add(self)

    @staticmethod
    def on_new_block_tx(db: DB, tx: TX) -> bool:
        """Correspond Addr's to TX."""

        addresses = set()

        vo_filt = lambda vo: "scriptPubKey" in vo and "addresses" in vo["scriptPubKey"]

        for vout in filter(vo_filt, tx.vouts_out):
            addresses.update(vout["scriptPubKey"]["addresses"])

        for vout in filter(vo_filt, tx.vouts_inp.values()):
            addresses.update(vout["scriptPubKey"]["addresses"])

        # TODO: Determine contract addresses from tx.logs

        from .addr import Addr

        addrs: List[Addr] = db.Session.query(
            Addr,
        ).join(
            AddrTX,
            AddrTX.addr_pk == Addr.pkid
        ).where(
            or_(
                Addr.addr_hy.in_(addresses),
                Addr.addr_hx.in_(addresses),
            )
        ).all()

        added = False

        for addr in addrs:
            uatx = AddrTX(addr=addr, tx=tx)
            uatx.on_new_tx(db)
            added = True

        return added


Index(AddrTX.__tablename__ + "_idx", AddrTX.addr_pk, AddrTX.tx_pk)
