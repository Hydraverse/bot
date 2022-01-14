from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from .db import DB
from .addr import Addr
from .smac import Smac

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

    def _removed_user(self, db: DB):


    def update_balance(self, db: DB):
        super().update_balance(db)

        for tokn_addr in self.tokn_addrs:
            tokn_addr.update_balance(db)


from .tokn_addr import ToknAddr
