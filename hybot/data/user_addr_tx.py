from __future__ import annotations
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index
from sqlalchemy.orm import relationship


from .base import *
from .tx import TX

__all__ = "UserAddrTX",


@dictattrs("date_create", "date_update", "user_addr_pk", "tx_pk")
class UserAddrTX(DbDateMixin, Base):
    __tablename__ = "user_addr_tx"
    __table_args__ = (
        UniqueConstraint("tx_pk", "user_addr_pk", name="_tx_user_addr_uc"),
    )

    tx_pk = Column(Integer, ForeignKey("tx.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    user_addr_pk = Column(Integer, ForeignKey("user_addr.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)

    tx = relationship("TX", back_populates="user_addr_txes", passive_deletes=True)
    user_addr = relationship("UserAddr", back_populates="user_addr_txes", passive_deletes=True)

    def __init__(self, tx: TX, user_addr, *args, **kwds):
        tx._added(user_addr)
        super().__init__(*args, tx=tx, user_addr=user_addr, **kwds)

    def _removed(self, db, user_addr):
        self.tx._removed(db, user_addr)


Index(UserAddrTX.__tablename__ + "_idx", UserAddrTX.user_addr_pk, UserAddrTX.tx_pk)
