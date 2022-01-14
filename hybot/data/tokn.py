from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from .db import DB
from .addr import Addr
from .smac import Smac
from .tx import TX

__all__ = "Tokn", "ToknAddr"


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

    def asdict(self):
        d = super().asdict()
        d.update({
            "symb": self.symb,
            "deci": self.deci,
            "supt": self.supt,
        })
        return d

    def update_balances(self, db: DB, tx: TX):
        super().update_balances(db, tx)

        tx_addrs = filter(lambda a: a != self, tuple(txa.addr for txa in tx.addr_txes))

        for tokn_addr in self.tokn_addrs:
            if tokn_addr.addr in tx_addrs:
                tokn_addr.update_balance(db)


from .tokn_addr import ToknAddr
