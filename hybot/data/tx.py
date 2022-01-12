from __future__ import annotations

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, String, UniqueConstraint, Integer, ForeignKey, SmallInteger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship

from .base import *

__all__ = "TX",


@dictattrs("pkid", "block_height", "block_txno", "block_txid", "vouts_inp", "vouts_out", "user_data")
class TX(DbPkidMixin, DbUserDataMixin, Base):
    __tablename__ = "tx"
    __table_args__ = (
        UniqueConstraint("block_pkid", "block_txno", name="_tx_block_pkid_txno_uc"),
    )

    block_pkid = Column(Integer, ForeignKey("block.pkid", ondelete="CASCADE"), nullable=False)
    block_txno = Column(SmallInteger, nullable=False)
    block_txid = Column(String(64), nullable=False, unique=True)
    vouts_inp = DbInfoColumn()
    vouts_out = DbInfoColumn()
    user_data = DbUserDataMixin.user_data()

    block = relationship("Block", back_populates="txes", passive_deletes=True)

    user_addr_txes = relationship(
        "UserAddrTX",
        back_populates="tx",
        cascade="all, delete-orphan",
        single_parent=True
    )

    # noinspection PyUnusedLocal
    def _removed(self, db, user_addr=None) -> bool:
        if not len(self.user_data):
            log.info(f"Deleting block #{self.block_height} TX #{self.block_tx_idx} with no user data.")
            db.Session.delete(self)
            return True
        else:
            log.info(f"Keeping block #{self.block_height} TX #{self.block_tx_idx} with non-empty user data.")

        return False

    def _load(self, db) -> bool:
        return True
