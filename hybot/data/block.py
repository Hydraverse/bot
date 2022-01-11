from __future__ import annotations

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, String, Integer, desc, or_, and_
from sqlalchemy.orm import relationship

from .base import *
from .addr import Addr
from .user_addr import UserAddr

__all__ = "Block",


@dictattrs("pkid", "date_create", "date_update", "height", "hash", "info", "data")
class Block(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "block"

    height = Column(Integer, nullable=False, unique=False, primary_key=False, index=True)
    hash = Column(String(64), nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    def _delete(self, db):
        if not len(self.user_blocks):
            if not len(self.data):
                log.info(f"Deleting block #{self.height} with no users and empty data.")
                db.Session.delete(self)
            else:
                log.info(f"Keeping block #{self.height} with no users and non-empty data.")

    def _load(self, db):
        n_tx = self.info.get("nTx", -1)

        if n_tx < 2:
            log.warning(f"Found {n_tx} TX in block, expected at least two.")
            return

        # First TX is coinbase input to the block.
        # Second TX is receiver TX to self + reward.
        self.info["coinbase"] = self.info["tx"][1]["vout"][1]["scriptPubKey"]["addresses"][0]

        addr_vout = {}
        addr_vin_vout = {}
        addrs_vio = set()

        vo_filt = lambda vo: hasattr(vo, "scriptPubKey") and hasattr(vo.scriptPubKey, "addresses")

        for tx in self.info["tx"][1:]:
            for vout in filter(vo_filt, tx.vout):
                for address in vout.scriptPubKey.addresses:
                    addrs_vio.add(address)
                    vout = AttrDict(vout)
                    vout.txid_ = tx.txid
                    addr_vout.setdefault(address, []).append(vout)

            for vin in filter(lambda vi: hasattr(vi, "txid"), tx.vin):
                vin_ = self.info["vin_vouts"][tx.txid][vin.txid]

                if vo_filt(vin_.vout):
                    for address in vin_.vout.scriptPubKey.addresses:
                        addrs_vio.add(address)
                        vin__vout = AttrDict(vin_.vout)
                        vin__vout.txid_ = tx.txid
                        addr_vin_vout.setdefault(address, []).append(vin__vout)

        addrs_hy = tuple(filter(lambda a: len(a) == 34, addrs_vio))
        addrs_hx = tuple(filter(lambda a: len(a) == 40, addrs_vio))

        user_addrs = db.Session.query(
            UserAddr
        ).join(
            Addr, and_(
                UserAddr.addr_pk == Addr.pkid,
                or_(
                    Addr.addr_hy.in_(addrs_hy),
                    Addr.addr_hx.in_(addrs_hx)
                )
            )
        ).all()

        db.Session.add(self)
        db.Session.commit()

        for address in addrs_vio:

            for user_addr in filter(lambda ua: str(ua.addr) == address, user_addrs):
                user_addr_data = user_addr.data.setdefault("b", AttrDict())

                if user_addr_data.get("h", 0) < self.height:
                    log.info(f"Adding block #{self.height} for user #{user_addr.user_pk} at addr {str(user_addr.addr)}")

                    user_addr_data.h = self.height

                    self.data.setdefault("map", {}).setdefault(str(user_addr.addr), []).append(user_addr.user_pk)

                    info_addr = AttrDict()
                    info_addr.height = self.height
                    info_addr.hash = self.hash
                    info_addr.minr = str(user_addr.addr) == self.info["coinbase"]
                    info_addr.vios = addr_vin_vout.get(address, [])
                    info_addr.vous = addr_vout.get(address, [])

                    user_addr_data.setdefault("map", {}).setdefault(self.hash, AttrDict()).update(info_addr)

                    db.Session.add(user_addr)

        if len(self.data):
            db.Session.add(self)
            db.Session.commit()
        else:
            log.debug(f"Skipping block #{self.height}.")
            db.Session.delete(self)
            db.Session.commit()

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

            for tx in info.tx:
                vinouts = Block.__get_vins(db.rpc, tx)

                if len(vinouts):
                    vin_vouts[tx.txid] = vinouts

            info.vin_vouts = vin_vouts

            info.conf = info.confirmations
            del info.confirmations
            del info.hash
            del info.height  # height == info.height

            new_block = Block(height=height, hash=bhash, info=info, data=AttrDict())
            new_block._load(db)

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

