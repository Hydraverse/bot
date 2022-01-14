from sqlalchemy import Column, Integer, ForeignKey, String

from .base import DbDataColumn
from .db import DB
from .addr import Addr
from .block import Block

__all__ = "Smac", "Tokn"


class Smac(Addr):
    __tablename__ = "smac"
    __mapper_args__ = {
        "polymorphic_identity": Addr.Type.S,
    }

    pkid = Column(Integer, ForeignKey("addr.pkid"), nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    stor = DbDataColumn()

    def __str__(self):
        return self.addr_hx

    def asdict(self):
        d = super().asdict()
        d.update({
            "name": self.name,
        })
        return d

    def on_new_block(self, db: DB, block: Block):
        # TODO: Optionally (?) also update name & Addr.validate_contract() info.
        self.stor = db.rpc.getstorage(self.addr_hx, self.block_h)
        super().on_new_block(db, block)

    def update_balance(self, db):
        # TODO: Implement this -- get HYDRA balance of smart contract
        #   (override super, do not call)
        pass


from .tokn import Tokn
