from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship

from hydra import log

from .base import *
from .db import DB
from .tokn import Tokn
from .addr import Addr

__all__ = "ToknAddr",


class ToknAddr(Base):
    __tablename__ = "tokn_addr"
    __table_args__ = (
        UniqueConstraint("tokn_pk", "addr_pk", name="_tokn_addr_uc"),
    )
    __mapper_args__ = {"eager_defaults": True}

    tokn_pk = Column(Integer, ForeignKey("tokn.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    balance = Column(Integer, nullable=True)

    tokn = relationship("Tokn", back_populates="tokn_addrs", foreign_keys=(tokn_pk,), passive_deletes=True)
    addr = relationship("Addr", back_populates="addr_tokns", foreign_keys=(addr_pk,), passive_deletes=True)

    def _remove(self, db: DB, tokn_addrs):
        tokn = self.tokn
        tokn_addrs.remove(self)
        tokn._removed_user(db)

    def update_balance(self, db: DB):
        balance = self.balance

        # TODO: Implement

        if balance != self.balance:
            self.balance = balance
            db.Session.add(self)

    @staticmethod
    def get_for(db: DB, tokn: Tokn, addr: Addr, create=True) -> Optional[ToknAddr]:
        if tokn.pkid is None or addr.pkid is None:
            if create:
                ta = ToknAddr(tokn=tokn, addr=addr)
                db.Session.add(ta)
                return ta
            else:
                return None

        ta: ToknAddr = db.Session.query(
            ToknAddr,
        ).where(
            and_(
                ToknAddr.tokn_pk == tokn.pkid,
                ToknAddr.addr_pk == addr.pkid
            )
        ).one_or_none()

        if ta is not None or not create:
            return ta

        ta = ToknAddr(tokn=tokn, addr=addr)
        db.Session.add(ta)
        return ta


Index(ToknAddr.__tablename__ + "_idx", ToknAddr.addr_pk, ToknAddr.tokn_pk)
