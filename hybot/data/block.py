from __future__ import annotations
import enum
from typing import Optional, Tuple
import binascii

from attrdict import AttrDict
from hydra import log
from hydra.app.txvio import TxVIOApp
from hydra.rpc.hydra_rpc import HydraRPC, BaseRPC
from sqlalchemy import Column, String, Enum, Integer, func, desc
from sqlalchemy.orm import relationship

from .base import *

__all__ = "Block",


@dictattrs("pkid", "date_create", "date_update", "height", "hash", "info", "data", "users")
class Block(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "block"

    height = Column(Integer, nullable=False, unique=True, primary_key=False, index=True)
    hash = Column(String(64), nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbInfoColumn()

    users = relationship(
        "UserBlock", back_populates="block", passive_deletes=True
    )

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
            vin_vouts = {}

            if info.get("nTx", 0) > 0:
                for tx in info.tx:
                    vinouts = Block.__get_vins(db.rpc, tx)

                    if len(vinouts):
                        vin_vouts[tx.txid] = vinouts

                info.vin_vouts = vin_vouts

                log.info(f"Adding block at height {height}")
                new_block = Block(height=height, hash=bhash, info=info)
                UserBlock._update_from_block(db, new_block)
                db.Session.add(new_block)

        db.Session.commit()

    @staticmethod
    def __get_vins(rpc, tx) -> dict:
        vins = {}

        for vin in filter(lambda vin_: hasattr(vin_, "txid"), tx.vin):

            vin_rawtx = rpc.getrawtransaction(vin.txid, False)

            vin_rawtx_decoded = rpc.decoderawtransaction(vin_rawtx, True)

            vin.vout = vin_rawtx_decoded.vout[vin.vout]

            txid = vin.txid
            del vin.txid
            vins[txid] = vin

        return vins

