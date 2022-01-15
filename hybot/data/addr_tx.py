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

    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    tx_pk = Column(Integer, ForeignKey("tx.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)

    addr = relationship("Addr", back_populates="addr_txes", passive_deletes=True)
    tx = relationship("TX", back_populates="addr_txes", passive_deletes=True)

    def _remove(self, db: DB, addr_txes):
        tx = self.tx
        addr_txes.remove(self)
        tx._removed_addr(db)

    def on_new_addr_tx(self, db: DB):
        self.addr.on_new_addr_tx(db, self)

    @staticmethod
    def on_new_block_tx(db: DB, tx: TX) -> bool:
        """Correspond Addr's to TX."""

        addresses_hy = set()
        addresses_hx = set()

        vo_filt = lambda vo: "scriptPubKey" in vo and "addresses" in vo["scriptPubKey"]

        for vout in filter(vo_filt, tx.vouts_out):
            addresses_hy.update(vout["scriptPubKey"]["addresses"])

        for vout in filter(vo_filt, tx.vouts_inp.values()):
            addresses_hy.update(vout["scriptPubKey"]["addresses"])

        for log_ in tx.logs:
            if "contractAddress" in log_:
                addresses_hx.add(log_["contractAddress"])

            if "from" in log_:
                addresses_hx.add(log_["from"])

            if "to" in log_:
                addresses_hx.add(log_["to"])

            for log__ in log_.log:
                addresses_hx.add(log__["address"])

        if not len(addresses_hy) and not len(addresses_hx):
            return False

        from .addr import Addr

        addrs: List[Addr] = db.Session.query(
            Addr,
        ).where(
            or_(
                Addr.addr_hy.in_(addresses_hy),
                Addr.addr_hx.in_(addresses_hx),
            )
        ).all()

        added = False

        uatxes = []

        for addr in addrs:
            uatx = AddrTX(addr=addr, tx=tx)
            uatxes.append(uatx)
            db.Session.add(uatx)
            added = True

        # Call after list is fully formed
        for uatx in uatxes:
            uatx.on_new_addr_tx(db)

        return added


Index(AddrTX.__tablename__ + "_idx", AddrTX.addr_pk, AddrTX.tx_pk)
