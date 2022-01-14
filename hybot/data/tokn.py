from sqlalchemy import Column, Integer, ForeignKey, String

from .db import DB
from .addr import Addr
from .smac import Smac

__all__ = "Tokn",


class Tokn(Smac):
    __tablename__ = "tokn"
    __mapper_args__ = {
        "polymorphic_identity": Addr.Type.T,
    }

    pkid = Column(Integer, ForeignKey("smac.pkid"), nullable=False, primary_key=True)
    symb = Column(String, nullable=False)
    deci = Column(Integer, nullable=False)
    supt = Column(Integer, nullable=False)

    def __str__(self):
        return self.addr_hx

    def update_balance(self, db: DB):
        # TODO: Implement this -- get token balances for associated addresses (maybe).
        #   (override super but also call)
        super().update_balance(db)
