from __future__ import annotations

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, String, Integer, desc, or_, and_, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import *
from .tx import TX

__all__ = "Block",


@dictattrs("pkid", "height", "hash", "info", "user_data")
class Block(DbPkidMixin, DbUserDataMixin, Base):
    __tablename__ = "block"
    __table_args__ = (
        UniqueConstraint("height", "hash", name="_block_height_hash_uc"),
    )

    height = Column(Integer, nullable=False, unique=False, primary_key=False, index=True)
    hash = Column(String(64), nullable=False, unique=True, primary_key=False, index=True)

    txes = relationship(
        "TX",
        back_populates="block",
        cascade="all, delete-orphan",
        single_parent=True
    )

    info = DbInfoColumn()
    user_data = DbUserDataMixin.user_data()

    def _delete_if_unused(self, db) -> bool:
        if not len(self.txes):
            if not len(self.user_data):
                log.info(f"Deleting block #{self.height} with no TXes and empty data.")
                db.Session.delete(self)
                return True
            else:
                log.info(f"Keeping block #{self.height} with no TXes and non-empty data.")

        return False

    def _load(self, db):
        n_tx = self.info.get("nTx", -1)

        if n_tx < 2:
            log.warning(f"Found {n_tx} TX in block, expected at least two.")
            return

        vo_filt = lambda vo: hasattr(vo, "scriptPubKey") and hasattr(vo.scriptPubKey, "addresses")
        added = False

        txes = self.info["tx"][1:]
        del self.info["tx"]

        for txno, votx in enumerate(txes):
            txno = txno + 1

            if not hasattr(votx, "vout"):
                continue

            vouts_inp = Block.__get_vout_inp(db.rpc, votx)
            vouts_out = [vout for vout in filter(vo_filt, votx.vout)]

            if len(vouts_out):
                tx = TX(
                    block=self,
                    block_txno=txno,
                    block_txid=votx.txid,
                    vouts_inp=vouts_inp,
                    vouts_out=vouts_out,
                )

                added |= tx._load(db)

        if added:
            db.Session.add(self)

        return added

    @staticmethod
    async def update(db) -> None:
        return await db.run_in_executor_session(Block._update, db)

    @staticmethod
    def _update(db) -> None:
        block = db.Session.query(
            Block.height
        ).order_by(
            desc(Block.height)
        ).limit(1).one_or_none()

        chain_height = db.rpc.getblockcount()

        for height in range(
                block.height + 1 if block is not None else chain_height, chain_height + 1
        ):
            bhash = db.rpc.getblockhash(height)
            info = db.rpc.getblock(bhash, verbosity=2)

            info.conf = info.confirmations
            del info.confirmations
            del info.hash
            del info.height  # height == info.height

            new_block = Block(height=height, hash=bhash, info=info)

            # Set PKID before load?
            # db.Session.add(new_block)
            # db.Session.commit()

            if not new_block._load(db):
                log.info(f"Discarding block without TXes at height {new_block.height}")
                db.Session.rollback()
            else:
                db.Session.commit()
                log.info(f"Added block with {len(new_block.txes)} TXes at height {new_block.height}")

    @staticmethod
    def __get_vout_inp(rpc, tx) -> dict:
        vout_inp = {}

        if hasattr(tx, "vin"):
            for vin in filter(lambda vin_: hasattr(vin_, "txid"), tx.vin):

                vin_rawtx = rpc.getrawtransaction(vin.txid, False)

                vin_rawtx_decoded = rpc.decoderawtransaction(vin_rawtx, True)

                vout_inp[vin.txid] = vin_rawtx_decoded.vout[vin.vout]

        return vout_inp

