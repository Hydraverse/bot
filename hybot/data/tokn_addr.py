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


class ToknAddr(DbPkidMixin, Base):
    __tablename__ = "tokn_addr"
    __table_args__ = (
        UniqueConstraint("tokn_pk", "addr_pk", name="_tokn_addr_uc"),
    )
    __mapper_args__ = {"eager_defaults": True}

    tokn_pk = Column(Integer, ForeignKey("tokn.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), nullable=False, primary_key=True, index=True)
    balance = Column(Integer, nullable=True)

    tokn = relationship("Tokn", back_populates="tokn_addrs", passive_deletes=True)
    addr = relationship("Addr", back_populates="addr_tokns", passive_deletes=True)

    tokn_addr_user_addrs = relationship(
        "UserToknAddr",
        back_populates="tokn_addr",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    def _remove(self, db: DB, tokn_addrs):
        tokn = self.tokn
        addr = self.addr

        if not len(self.tokn_addr_user_addrs):
            log.info(f"Deleting info for token {str(self.tokn)} at addr {str(self.addr)} - no subscriptions.")
            db.Session.delete(self)

        tokn_addrs.remove(self)
        tokn._removed_user(db)
        addr._removed_user(db)

    def update_balance(self, db: DB):
        # TODO: Implement
        pass

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
