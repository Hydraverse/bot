from __future__ import annotations
import enum
from functools import lru_cache
from typing import Optional, Tuple
import binascii

from attrdict import AttrDict
from hydra import log
from hydra.rpc.hydra_rpc import BaseRPC, HydraRPC
from sqlalchemy import Column, String, Enum, Integer, ForeignKey
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import relationship, lazyload

from .base import *
from .db import DB
from .block import Block, TX
from .addr_tx import AddrTX

__all__ = "Addr", "AddrTX", "Smac", "Tokn"


@dictattrs("pkid", "date_create", "date_update", "addr_tp", "addr_hx", "addr_hy", "block_h", "balance")
class Addr(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "addr"

    class Type(enum.Enum):
        H = "HYDRA"
        S = "smart contract"
        T = "token"

        @staticmethod
        def by_len(address: str) -> Optional[Addr.Type]:
            length = len(address)

            return (
                Addr.Type.H if length == 34 else
                Addr.Type.S if length == 40 else
                None
            )

    addr_tp = Column(Enum(Type, validate_strings=True), nullable=False, index=True)
    addr_hx = Column(String(40), nullable=False, unique=True, index=True)
    addr_hy = Column(String(34), nullable=False, unique=True, index=True)
    block_h = Column(Integer, nullable=True, index=True)
    balance = Column(Integer, nullable=True)

    user_addrs = relationship(
        "UserAddr",
        back_populates="addr",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    addr_txes = relationship(
        "AddrTX",
        back_populates="addr",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    addr_tokns = relationship(
        "ToknAddr",
        back_populates="addr",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": Type.H,
        "polymorphic_on": addr_tp
    }

    @staticmethod
    def make(addr_tp: Type, addr_hx: str, addr_hy: str, **kwds) -> [Addr, Smac, Tokn]:
        if addr_tp == Addr.Type.H:
            return Addr(addr_hx=addr_hx, addr_hy=addr_hy, **kwds)
        elif addr_tp == Addr.Type.S:
            return Smac(addr_hx=addr_hx, addr_hy=addr_hy, **kwds)
        elif addr_tp == Addr.Type.T:
            return Tokn(addr_hx=addr_hx, addr_hy=addr_hy, **kwds)
        else:
            return Addr(addr_tp=addr_tp, addr_hx=addr_hx, addr_hy=addr_hy, **kwds)

    def __str__(self):
        return self.addr_hy

    def on_new_addr_tx(self, db: DB, addr_tx: AddrTX):
        tx = addr_tx.tx
        if self.block_h != tx.block.height:
            self.block_h = tx.block.height
            self.on_new_block(db, tx.block)

        self.on_new_tx(db, tx)

    def on_new_block(self, db: DB, block: Block):
        pass

    def on_new_tx(self, db: DB, tx: TX):
        self.update_balances(db, tx)

    # noinspection PyUnusedLocal
    def update_balances(self, db: DB, tx: TX):
        balance = int(db.rpc.getbalanceofaddress(self.addr_hy) * 10**8)

        if self.balance != balance:
            self.balance = balance
            db.Session.add(self)

    # noinspection PyPep8Naming
    def __UNUSED_ensure_imported(self, db: DB):
        if self.addr_tp == Addr.Type.H:
            if self.addr_hy not in db.rpc.listlabels():
                log.info(f"Importing address {self.addr_hy}")
                db.rpc.importaddress(self.addr_hy, self.addr_hy)

    def _removed_user(self, db: DB):
        if not len(self.user_addrs):
            for addr_tx in list(self.addr_txes):
                addr_tx._remove(db, self.addr_txes)

            for addr_tokn in list(self.addr_tokns):
                addr_tokn._remove(db, self.addr_tokns)

            log.info(f"Deleting {self.addr_tp.value} address {str(self)} with no users.")
            db.Session.delete(self)

    @staticmethod
    def get(db: DB, address: str, create=True) -> [Addr, Smac, Tokn]:
        addr_tp, addr_hx, addr_hy, addr_attr = Addr.normalize(db, address)

        try:
            if addr_tp == Addr.Type.T:
                q: Tokn = db.Session.query(Tokn).where(
                    Tokn.addr_hx == addr_hx
                )
            elif addr_tp == Addr.Type.S:
                q: Smac = db.Session.query(Smac).where(
                    Smac.addr_hx == addr_hx
                )
            else:
                q: Addr = db.Session.query(Addr).where(
                    Addr.addr_hx == addr_hx,
                    Addr.addr_tp == addr_tp
                )

            if not create:
                return q.one_or_none()

            return q.one()

        except NoResultFound:
            addr: [Addr, Smac, Tokn] = Addr.make(addr_tp, addr_hx, addr_hy, **addr_attr)
            db.Session.add(addr)
            db.Session.commit()
            return addr

    @staticmethod
    @lru_cache(maxsize=None)
    def validate(db: DB, address: str):
        av = db.rpc.validateaddress(address)
        return av

    @staticmethod
    @lru_cache(maxsize=None)
    def normalize(db: DB, address: str) -> Tuple[Addr.Type, str, str, AttrDict]:
        """Normalize an input address into a tuple of (Addr.Type, addr_hex, addr_hydra).
        Or raise ValueError.
        """
        addr_tp = Addr.Type.by_len(address)
        attrs = AttrDict()

        if addr_tp is None:
            raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (bad length)")

        if addr_tp == Addr.Type.H:

            valid = Addr.validate(db, address)

            if not valid.isvalid:
                raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (validation failed)")

            addr_hy = valid.address
            addr_hx = db.rpc.gethexaddress(address)

        elif addr_tp == Addr.Type.S:

            try:
                addr_hx = hex(int(address, 16))[2:].rjust(40, "0")  # ValueError on int() fail
            except ValueError:
                raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (conversion failed)")

            addr_hy = db.rpc.fromhexaddress(addr_hx)

            addr_tp, attrs = Addr.__validate_contract(db, addr_hx)

        else:
            raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (bad type)")

        return addr_tp, addr_hx, addr_hy, attrs

    @staticmethod
    def __validate_contract(db: DB, addr_hx: str) -> Tuple[Addr.Type, AttrDict]:

        sci = AttrDict()
        addr_tp = Addr.Type.S

        try:
            # Raises BaseRPC.Exception if address does not exist
            r = db.rpc.callcontract(addr_hx, "06fdde03")  # name()
        except BaseRPC.Exception:
            # Safest assumption is that this is actually a HYDRA hex address
            return Addr.Type.H, sci

        if r.executionResult.excepted == "None":
            sci.name = Addr.__sc_out_str(
                r.executionResult.output[128:]
            )

        r = db.rpc.callcontract(addr_hx, "95d89b41")  # symbol()

        if r.executionResult.excepted == "None":
            symb = Addr.__sc_out_str(
                r.executionResult.output[128:]
            )

            r = db.rpc.callcontract(addr_hx, "313ce567")  # decimals()

            if r.executionResult.excepted == "None":
                deci = int(r.executionResult.output, 16)

                r = db.rpc.callcontract(addr_hx, "18160ddd")  # totalSupply()

                if r.executionResult.excepted == "None":
                    sci.symb = symb
                    sci.deci = deci
                    sci.supt = int(r.executionResult.output, 16)
                    addr_tp = Addr.Type.T

        return addr_tp, sci

    @staticmethod
    def __sc_out_str(val):
        return binascii.unhexlify(val).replace(b"\x00", b"").decode("utf-8")


from .smac import Smac, Tokn
