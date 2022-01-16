from typing import Optional

from hydra import log
from hydra.rpc.base import BaseRPC
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import dictattrs
from .db import DB
from .addr import Addr
from .smac import Smac
from .tx import TX

__all__ = "Tokn", "ToknAddr"


@dictattrs("symb", "deci", "supt")
class Tokn(Smac):
    __tablename__ = "tokn"
    __mapper_args__ = {
        "polymorphic_identity": Addr.Type.T,
    }

    pkid = Column(Integer, ForeignKey("smac.pkid"), nullable=False, primary_key=True)
    symb = Column(String, nullable=False)
    deci = Column(Integer, nullable=False)
    supt = Column(Integer, nullable=False)

    tokn_addrs = relationship(
        "ToknAddr",
        back_populates="tokn",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    def __str__(self):
        return self.addr_hx

    def balance_of(self, db: DB, addr: Addr) -> Optional[int]:
        try:
            for qbal in addr.info.get("qrc20Balances", {}):
                if qbal.get("addressHex", ...) == self.addr_hx:
                    return qbal["balance"]

            return self.__balance_of_rpc(db, addr)
        except BaseRPC.Exception as exc:
            log.critical(f"Tokn RPC error: {str(exc)}", exc_info=exc)
            return None

    def __balance_of_rpc(self, db: DB, addr: Addr) -> Optional[int]:
        r = db.rpc.callcontract(self.addr_hx, "70a08231" + addr.addr_hx.rjust(64, "0"))  # balanceOf(address)

        if r.executionResult.excepted != "None":
            log.warning(f"Contract call failed: {r.executionResult.excepted}")
            log.debug(f"Contract call failed (full result): {r}")
            return None

        return int(r.executionResult.output, 16)

    def apply_deci(self, balance: int) -> str:
        return str(balance / 10**self.deci)  # TODO: Apply decimal manually or use library.

    def populate_balances(self, db: DB):
        for tokn_addr in self.tokn_addrs:
            tokn_addr.update_balance(db)

    def update_balances(self, db: DB, tx: Optional[TX]):
        super().update_balances(db, tx)

        if tx is not None:
            for tx_addr in filter(lambda txa: txa.addr, tx.addr_txes):
                tokn_addr = ToknAddr.get_for(db, self, tx_addr.addr, create=True)
                tokn_addr.update_balance(db, tx)


from .tokn_addr import ToknAddr
