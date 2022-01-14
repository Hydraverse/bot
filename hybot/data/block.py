from __future__ import annotations

import asyncio

from hydra import log
from sqlalchemy import Column, String, Integer, desc, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import *
from .db import DB

__all__ = "Block", "TX"


class LocalState:
    # Testnet blocks:
    # 160387 (160388 is HYDRA SC TX + minting two tokens to sender)
    # 160544 (160545 is HYDRA TX)
    height = 0
    hash = ""


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
    logs = DbInfoColumn()
    user_data = DbUserDataMixin.user_data()

    def _delete_if_unused(self, db: DB) -> bool:
        if not len(self.txes):
            if not len(self.user_data):
                log.info(f"Deleting block #{self.height} with no TXes and empty data.")
                db.Session.delete(self)
                return True
            else:
                log.info(f"Keeping block #{self.height} with no TXes and non-empty data.")

        return False

    def on_new_block(self, db: DB) -> bool:
        n_tx = self.info.get("nTx", -1)

        if n_tx < 2:
            log.warning(f"Found {n_tx} TX in block, expected at least two.")
            return False

        vo_filt = lambda vo: hasattr(vo, "scriptPubKey") and hasattr(vo.scriptPubKey, "addresses")
        added = False

        for txno, votx in enumerate(list(self.info["tx"])):
            votx.n = txno  # Preserve ordering info after deletion.

            logs = list(filter(lambda lg: lg.transactionHash == votx.txid, self.logs))

            for log_ in logs:
                del log_.blockHash
                del log_.blockNumber
                del log_.transactionHash
                del log_.transactionIndex

            if hasattr(votx, "vout"):
                vouts_inp = Block.__get_vout_inp(db.rpc, votx)
                vouts_out = [vout for vout in filter(vo_filt, votx.vout)]

                if len(vouts_out):
                    tx = TX(
                        block=self,
                        block_txno=txno,
                        block_txid=votx.txid,
                        vouts_inp=vouts_inp,
                        vouts_out=vouts_out,
                        logs=logs
                    )

                    if not tx.on_new_block(db):
                        self.txes.remove(tx)
                    else:
                        self.info["tx"].remove(votx)  # Leave behind the unprocessed TXes
                        added = True

        if added:
            db.Session.add(self)

        return added

    @staticmethod
    async def update_task(db: DB) -> None:
        # await asyncio.sleep(30)

        while 1:
            await Block.update(db)
            await asyncio.sleep(15)

    @staticmethod
    async def update(db: DB) -> None:
        # noinspection PyBroadException
        try:
            if LocalState.height == 0:
                await db.run_in_executor_session(Block.__update_init, db)

            return await db.run_in_executor_session(Block.__update, db)
        except BaseException as exc:
            log.critical(f"Block.update exception: {str(exc)}", exc_info=exc)

    @staticmethod
    def __update_init(db: DB) -> None:
        block: Block = db.Session.query(
            Block
        ).order_by(
            desc(Block.height)
        ).limit(1).one_or_none()

        if block is not None:
            LocalState.height = block.height
            LocalState.hash = block.hash
        else:
            LocalState.height = db.rpc.getblockcount() - 1

    @staticmethod
    def __update(db: DB) -> None:

        chain_height = db.rpc.getblockcount()
        chain_hash = db.rpc.getblockhash(chain_height)

        log.debug(f"Poll: chain={chain_height} local={LocalState.height}")

        if chain_height == LocalState.height:
            if chain_hash != LocalState.hash:
                log.warning(f"Fork detected at height {chain_height}: {chain_hash} != {LocalState.hash}")
            else:
                return

        for height in range(LocalState.height + 1, chain_height + 1):
            bhash = db.rpc.getblockhash(height)

            new_block: Block = Block(
                height=height,
                hash=bhash,
                info=Block.__get_block_info(db, bhash),
                logs=db.rpc.searchlogs(height, height)
            )

            if not new_block.on_new_block(db):
                log.debug(f"Discarding block without TXes at height {new_block.height}")
                db.Session.rollback()
            else:
                log.info(f"Added block with {len(new_block.txes)} TX(es) at height {new_block.height}")
                db.Session.commit()

        LocalState.height = chain_height
        LocalState.hash = chain_hash

    @staticmethod
    def __get_block_info(db: DB, block_hash: str):
        info = db.rpc.getblock(block_hash, verbosity=2)

        info.conf = info.confirmations
        del info.confirmations
        del info.hash
        del info.height

        return info

    @staticmethod
    def __get_vout_inp(rpc, tx) -> dict:
        vout_inp = {}

        if hasattr(tx, "vin"):
            for vin in filter(lambda vin_: hasattr(vin_, "txid"), tx.vin):

                vin_rawtx = rpc.getrawtransaction(vin.txid, False)

                vin_rawtx_decoded = rpc.decoderawtransaction(vin_rawtx, True)

                vout_inp[vin.txid] = vin_rawtx_decoded.vout[vin.vout]

        return vout_inp


from .tx import TX
