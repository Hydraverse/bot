from __future__ import annotations

from typing import Optional, List

from attrdict import AttrDict
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *
from .db import DB
from .addr import Addr
from .tokn_addr import ToknAddr

__all__ = "UserTokn",


@dictattrs("user", "tokn")
class UserTokn(Base):
    __tablename__ = "user_tokn"
    __table_args__ = (
        UniqueConstraint("user_pk", "tokn_pk", name="_user_tokn_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    tokn_pk = Column(Integer, ForeignKey("tokn.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    user = relationship("User", back_populates="user_tokns", passive_deletes=True)
    tokn = relationship("Tokn", passive_deletes=True)

    def _remove(self, db: DB, user_tokns):
        tokn = self.tokn
        user_tokns.remove(self)
        tokn._removed_user(db)

    def get_tokn_addr(self, db: DB, addr: Addr, create=True) -> Optional[ToknAddr]:
        return ToknAddr.get_for(db, self.tokn, addr, create=create)


Index(UserTokn.__tablename__ + "_idx", UserTokn.user_pk, UserTokn.tokn_pk)
