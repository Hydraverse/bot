from typing import Tuple, List

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, ForeignKey, Integer, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import lazyload, relationship

from hybot.data.base import *
from .block import Block
from .addr import Addr

__all__ = "UserBlock",


@dictattrs("user_pk", "block_pk", "date_create", "date_update", "info", "data")
class UserBlock(DbDateMixin, Base):
    __tablename__ = "user_block"

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    block_pk = Column(Integer, ForeignKey("block.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()

    user = relationship("User", back_populates="blocks")
    block = relationship("Block", back_populates="users")

    @staticmethod
    def _update_from_block(db, block: Block):
        if block.info.nTx < 2:
            return
    
        # First TX is coinbase input to the block.
        # Second TX is receiver TX to self + reward.
        coinbase_dst_addr = block.info.tx[1].vout[1].scriptPubKey.addresses[0]
    
        addr_vout = {}
        addr_vin_vout = {}
        addrs_vio = set()
    
        vo_filt = lambda vo: hasattr(vo, "scriptPubKey") and hasattr(vo.scriptPubKey, "addresses")
    
        for tx in block.info.tx[1:]:
            for vout in filter(vo_filt, tx.vout):
                for address in vout.scriptPubKey.addresses:
                    addrs_vio.add(address)
                    addr_vout.setdefault(address, []).append(vout)
    
            for vin in filter(lambda vi: hasattr(vi, "txid"), tx.vin):
                vin_ = block.info.vin_vouts[tx.txid][vin.txid]
    
                for address in vin_.vout.scriptPubKey.addresses:
                    addrs_vio.add(address)
                    addr_vin_vout.setdefault(address, []).append(vin_.vout)
    
        addrs_hy = tuple(filter(lambda a: len(a) == 34, addrs_vio))
        addrs_hx = tuple(filter(lambda a: len(a) == 40, addrs_vio))
    
        addrs = db.Session.query(
            Addr
        ).filter(
            or_(
                Addr.addr_hy.in_(addrs_hy),
                Addr.addr_hx.in_(addrs_hx)
            )
        ).all()  # TODO: Try .where(Addr.users.any()) ?
    
        for address in addrs_vio:
            addr_filt = lambda ao: (len(address) == 34 and ao.addr_hy == address) or (len(address) == 40 and ao.addr_hx == address)
    
            for addr in filter(lambda a: addr_filt(a) and len(a.users) > 0, addrs):
                if addr.data.setdefault("b", block.info.height) < block.info.height:
                    addr.data.b = block.info.height
                    db.Session.add(addr)
    
                    for user in addr.users:
                        user._update_from_block_tx(
                            db, addr, address, coinbase_dst_addr, block.info,
                            addr_vin_vout.get(address, []),
                            addr_vout.get(address, [])
                        )
        #
        # Caller handles db.Session.commit()
        #


