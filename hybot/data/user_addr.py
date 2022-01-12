from __future__ import annotations
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint, Index, and_
from sqlalchemy.orm import relationship


from .base import *
from .user_addr_tx import UserAddrTX, TX

__all__ = "UserAddr",


@dictattrs("pkid", "user_pk", "addr_pk", "date_create", "date_update", "info", "data", "user", "addr")
class UserAddr(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "user_addr"
    __table_args__ = (
        UniqueConstraint("user_pk", "addr_pk", name="_user_addr_uc"),
    )

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=False, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()

    user = relationship("User", back_populates="user_addrs", passive_deletes=True)
    addr = relationship("Addr", back_populates="user_addrs", passive_deletes=True)

    user_addr_txes = relationship(
        UserAddrTX,
        back_populates="user_addr",
        cascade="all, delete-orphan",
        single_parent=True
    )

    def _delete(self, db):
        # self.user.user_addrs.remove(self)

        for user_addr_tx in self.user_addr_txes:
            self.user_addr_txes.remove(user_addr_tx)
            user_addr_tx._removed(db, self)

        self.addr._delete(db)

    def _add_tx(self, db, tx: TX) -> UserAddrTX:
        user_addr_tx = UserAddrTX(tx=tx, user_addr=self)
        self.user_addr_txes.add(user_addr_tx)
        db.Session.add(self)
        return user_addr_tx

    def _del_tx(self, db, tx: TX):
        user_addr_tx = db.Session.query(
            UserAddrTX,
        ).where(
            and_(
                UserAddrTX.tx_pk == tx.pkid,
                UserAddrTX.user_addr_pk == self.pkid,
            )
        ).one()

        self.user_addr_txes.remove(user_addr_tx)
        user_addr_tx._removed(db, self)
        db.Session.add(self)

    @staticmethod
    async def update_all(db) -> None:
        return await db.run_in_executor_session(UserAddr._update_all, db)

    @staticmethod
    def _update_all(db) -> None:
        """Update from the latest known block.
        """
        user_addrs = db.Session.query(
            UserAddr,
        ).all()

        update_addrs = {
            str(ua.addr): ua
            for ua in user_addrs
        }

        if not update_addrs:
            return



    def _update(self, db, block_info):
        pass


Index(UserAddr.__tablename__ + "_idx", UserAddr.user_pk, UserAddr.addr_pk)
