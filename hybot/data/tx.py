from __future__ import annotations
from hydra import log
from sqlalchemy import Column, String, UniqueConstraint, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship

from .base import *

__all__ = "TX",


@dictattrs("pkid", "date_create", "date_update", "info", "data")
class TX(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "tx"
    __table_args__ = (
        UniqueConstraint("block_height", "block_hash", name="_tx_block_height_hash_uc"),
    )

    block_tx_index = Column(Integer, nullable=False)
    block_height = Column(String(64), nullable=False)
    block_hash = Column(String(64), nullable=False, unique=True)
    txid = Column(String(64), nullable=False, unique=True)
    vouts_inp = DbInfoColumn()
    vouts_out = DbInfoColumn()
    user_pkid = DbInfoColumn()
    info = DbInfoColumn()
    data = DbDataColumn()

    user_addr_txes = relationship(
        "UserAddrTX",
        back_populates="tx"
    )

    def __init__(self, *args, **kwds):
        self.user_pkid = []
        super().__init__(*args, **kwds)

    def user_pkid_add(self, user_pk: int):
        self.user_pkid.append(user_pk)

    def user_pkid_del(self, user_pk: int):
        self.user_pkid.remove(user_pk)

    def _added(self, user_addr):
        self.user_pkid_add(user_addr.user.pkid)

    def _removed(self, db, user_addr):
        self.user_pkid_del(user_addr.user.pkid)

        if not len(self.user_addr_txes):
            if len(self.user_pkid):
                raise RuntimeError("Some user_pkid's are not attached to user_addrs! (while deleting TX from user_addr_txes).")
            elif not len(self.data):
                log.info(f"Deleting TX with no user_addrs and no data: {self.txid}.")
                db.Session.delete(self)
            else:
                log.debug(f"Keeping TX with no user_addrs and non-empty data: {self.txid}.")
