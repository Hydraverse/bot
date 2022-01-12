from __future__ import annotations

from hydra import log
from sqlalchemy import Column, String, UniqueConstraint, Integer, ForeignKey, SmallInteger
from sqlalchemy.orm import relationship

from .base import *
from .user_addr_tx import UserAddrTX

__all__ = "TX", "UserAddrTX"


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
    def _removed(self, db, user_addr_tx) -> bool:
        if len(self.user_addr_txes) == 1 and self.user_addr_txes[0] == user_addr_tx:
            if not len(self.user_data):
                log.info(f"Deleting TX #{self.block_txno} from block #{self.block.height}.")
                db.Session.delete(self)
                self.block._delete_if_unused(db)
                return True
            else:
                log.info(f"Keeping TX #{self.block_txno} from block #{self.block.height} with non-empty user data.")

        return False

    def _load(self, db) -> bool:
        if not UserAddrTX._load(db, self):
            log.debug(f"Not adding TX #{self.block_txno} from block #{self.block.height} with no current subscribers.")
            return False

        log.info(f"Adding TX #{self.block_txno} from block #{self.block.height} with {len(self.user_addr_txes)} subscriber(s).")
        db.Session.add(self)
        return True

