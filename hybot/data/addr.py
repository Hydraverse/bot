from __future__ import annotations
import enum
from typing import Optional, Tuple

from sqlalchemy import Column, String, Enum, BigInteger
from sqlalchemy.orm import relationship

from .base import *

__all__ = "Addr",


@dictattrs("pkid", "addr_tp", "addr_hx", "addr_hy", "date_create", "date_update", "info", "data", "users")
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

    date_create = DbDateMixin.date_create()
    date_update = DbDateMixin.date_update()

    info = DbInfoColumn()
    data = DbDataColumn()

    users = relationship("User", secondary="user_addr", back_populates="addrs", passive_deletes=True)

    @staticmethod
    async def validate_address(db, address: str):
        return await type(db).run_in_executor(Addr._validate_address, db, address)

    @staticmethod
    def _validate_address(db, address: str):
        return db.rpc.validateaddress(address)

    @staticmethod
    async def addr_normalize(db, address: str) -> Tuple[Addr.Type, str, str]:
        return await type(db).run_in_executor(Addr._addr_normalize, db, address)

    @staticmethod
    def _addr_normalize(db, address: str) -> Tuple[Addr.Type, str, str]:
        """Normalize an input address into a tuple of (Addr.Type, addr_hex, addr_hydra).
        Or raise ValueError.
        """

        by_len = Addr.Type.by_len(address)

        if by_len is None:
            raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (bad length)")

        if by_len == Addr.Type.H:

            valid = db.rpc.validateaddress(address)

            if not valid.isvalid:
                raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (validation failed)")

            addr_hy = valid.address
            addr_hx = db.rpc.gethexaddress(address)

        elif by_len == Addr.Type.S:

            addr_hx = hex(int(address, 16))[2:]
            addr_hy = db.rpc.fromhexaddress(addr_hx)  # ValueError on int() fail

            # TODO: Determine if addr type is token

        else:
            raise ValueError(f"Invalid HYDRA or smart contract address '{address}' (bad type)")

        return by_len, addr_hx, addr_hy


