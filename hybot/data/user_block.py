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


@dictattrs("date_create", "date_update", "user_pk", "block_pk", "addr_pk", "info", "data")
class UserBlock(DbDateMixin, Base):
    __tablename__ = "user_block"

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    block_pk = Column(Integer, ForeignKey("block.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()

    user = relationship("User", back_populates="blocks")
    block = relationship("Block", back_populates="users")
    addr = relationship("Addr")

    @staticmethod
    def _update_from_block(db, block: Block):
        nTx = block.info.get("nTx", -1)

        if nTx < 2:
            log.warning(f"Found {nTx} TX in block, expected at least two.")
            return
    
        # First TX is coinbase input to the block.
        # Second TX is receiver TX to self + reward.
        block.info["coinbase"] = block.info["tx"][1]["vout"][1]["scriptPubKey"]["addresses"][0]
    
        addr_vout = {}
        addr_vin_vout = {}
        addrs_vio = set()
    
        vo_filt = lambda vo: hasattr(vo, "scriptPubKey") and hasattr(vo.scriptPubKey, "addresses")
    
        for tx in block.info["tx"][1:]:
            for vout in filter(vo_filt, tx.vout):
                for address in vout.scriptPubKey.addresses:
                    addrs_vio.add(address)
                    addr_vout.setdefault(address, []).append(vout)
    
            for vin in filter(lambda vi: hasattr(vi, "txid"), tx.vin):
                vin_ = block.info["vin_vouts"][tx.txid][vin.txid]
    
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
            addr_filt = lambda ao, a: (len(a) == 34 and ao.addr_hy == a) or (len(a) == 40 and ao.addr_hx == a)
    
            for addr in filter(lambda adr: addr_filt(adr, address) and len(adr.users) > 0, addrs):
                if addr.data.setdefault("b", block.height) < block.height:
                    addr.data.b = block.height
    
                    for user_addr in addr.users:
                        info = AttrDict()
                        info.minr = addr_filt(addr, block.info["coinbase"])
                        info.vios = addr_vin_vout.get(address, [])
                        info.vous = addr_vout.get(address, [])

                        log.info(f"Adding{' mined' if info.minr else ''} block #{block.height} for user #{user_addr.user.pkid} at addr {str(addr)}")
                        user_block = UserBlock(user=user_addr.user, block=block, addr=addr, info=info)
                        db.Session.add(user_block)

                    db.Session.add(addr)
        #
        # Caller handles db.Session.commit()
        #


