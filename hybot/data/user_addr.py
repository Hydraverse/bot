from __future__ import annotations
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship


from .base import *

__all__ = "UserAddr",


@dictattrs("user_pk", "addr_pk", "date_create", "date_update", "info", "data", "user", "addr")
class UserAddr(DbDateMixin, Base):
    __tablename__ = "user_addr"

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()

    user = relationship("User", back_populates="user_addrs")
    addr = relationship("Addr", back_populates="user_addrs")

    def _delete(self, db):
        self.user.user_addrs.remove(self)
        self.addr._delete(db)

    @staticmethod
    async def update(
            db, user_pk: int, addr_pk: int,
            info: dict, data: dict = None, over: bool = False) -> None:
        if (info is None and data is None) or (over and (not info or not data)):
            return

        return await db.run_in_executor_session(UserAddr._update, db, user_pk, addr_pk, info, data, over)

    @staticmethod
    def _update(db, user_pk: int, addr_pk: int, info: dict, data: dict, over: bool) -> None:
        ua: UserAddr = db.Session.query(UserAddr).where(
            UserAddr.user_pk == user_pk and
            UserAddr.addr_pk == addr_pk
        ).one()

        if over:
            if info is not None:
                ua.info = info
            if data is not None:
                ua.data = data
        else:
            if info is not None:
                ua.info.update(info)
            if data is not None:
                ua.data.update(data)

        db.Session.add(ua)
        db.Session.commit()


