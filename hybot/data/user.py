from __future__ import annotations
from typing import Optional

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, Integer, and_
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import relationship, lazyload

from .base import *
from .addr import Addr
from .block import Block
from .user_pkid import UserPkid, DbUserPkidMixin
from .user_addr import UserAddr
from .user_block import UserBlock

__all__ = "User", "UserPkid", "UserAddr", "UserBlock"


@dictattrs("pkid", "name", "user_id", "date_create", "date_update", "info", "data")
class User(DbUserPkidMixin, DbDateMixin, Base):
    __tablename__ = "user"

    pkid = DbUserPkidMixin.pkid()
    name = DbUserPkidMixin.name()

    user_id = Column(Integer, nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    addrs = relationship(UserAddr, back_populates="user", cascade="all, delete")

    blocks = relationship(
        UserBlock, back_populates="user", cascade="all, delete",
        order_by="desc(UserBlock.block_pk)"
    )

    def __str__(self):
        return f"{self.pkid} [{self.name}] {self.user_id}"

    def attrdict(self, full=False):
        user_dict = AttrDict(self.asdict())

        if full:
            user_dict.addrs = list(AttrDict(ua.asdict()) for ua in self.addrs)
            user_dict.blocks = list(AttrDict(ub.asdict()) for ub in self.blocks)

        return user_dict

    def _update_from_block_tx(self, db, addr, address, address_coinbase, block_info, inp_vouts, out_vouts):
        nq = self.data.setdefault("nq", [])

        pass

    @staticmethod
    async def get_pkid(db, user_id: int) -> Optional[int]:
        return await db.run_in_executor_session(User._get_pkid, db, user_id)

    @staticmethod
    def _get_pkid(db, user_id: int) -> Optional[int]:
        u = (
            db.Session.query(
                User.pkid
            ).filter(
                User.user_id == user_id
            ).one_or_none()
        )

        return u.pkid if u is not None else None

    @staticmethod
    async def load(db, user_id: int, create: bool = True, full: bool = False) -> Optional[AttrDict]:
        return await db.run_in_executor_session(User._load, db, user_id, create, full)

    @staticmethod
    def _load(db, user_id: int, create: bool, full: bool) -> Optional[AttrDict]:

        u: User = db.Session.query(
            User
        ).filter(
            User.user_id == user_id
        ).one_or_none()

        if u is not None:
            return u.attrdict(full=full)

        elif not create:
            return None

        while True:
            pkid = UserPkid()

            try:
                db.Session.add(pkid)
                db.Session.commit()
                break
            except IntegrityError:
                db.Session.rollback()
                log.error("User unique PKID name clash! Trying again.")
                continue

        user_ = User(
            pkid=pkid.pkid,
            name=pkid.name,
            user_id=user_id,
        )

        db.Session.add(user_)
        db.Session.commit()

        return user_.attrdict(full=full)

    @staticmethod
    async def update_info(db, user_pk: int, info: dict, data: dict = None, over: bool = False) -> None:
        if (info is None and data is None) or (over and (not info or not data)):
            return
        return await db.run_in_executor_session(User._update_info, db, user_pk, info, data, over)

    @staticmethod
    def _update_info(db, user_pk: int, info: dict, data: dict, over: bool) -> None:
        u: User = db.Session.query(User).where(
            User.pkid == user_pk
        ).options(
            lazyload(User.addrs),
            lazyload(User.blocks),
        ).one()

        if over:
            if info is not None:
                u.info = info
            if data is not None:
                u.data = data
        else:
            if info is not None:
                u.info.update(info)
            if data is not None:
                u.data.update(data)

        db.Session.add(u)
        db.Session.commit()

    @staticmethod
    async def delete(db, user_id: int) -> None:
        return await db.run_in_executor_session(User._delete, db, user_id)

    @staticmethod
    def _delete(db, user_id: int) -> None:
        u: User = db.Session.query(User).where(
            User.user_id == user_id
        ).one_or_none()

        if u is not None:
            return u.__delete(db)

    def __delete(self, db):
        for user_addr in self.addrs:
            self.addrs.remove(user_addr)
            if not len(user_addr.addr.users):
                if not len(user_addr.addr.info):
                    log.info(f"Deleting address with no users and empty info: {str(user_addr)}")
                    db.Session.delete(user_addr.addr)
                else:
                    log.info(f"Keeping address with no users and non-empty info: {str(user_addr)}")

        db.Session.delete(self)
        db.Session.commit()

    @staticmethod
    async def addr_add(db, user_pk: int, address: str) -> AttrDict:
        return await db.run_in_executor_session(User._addr_add, db, user_pk, address)

    @staticmethod
    def _addr_add(db, user_pk: int, address: str) -> AttrDict:
        u = db.Session.query(
            User
        ).where(
            User.pkid == user_pk
        ).options(
            lazyload(User.addrs),
            lazyload(User.blocks)
        ).one()

        user_addr = u.__addr_add(db, address)
        db.Session.commit()
        return AttrDict(user_addr.asdict())

    def __addr_add(self, db, address: str) -> UserAddr:
        addr = Addr._load(db, address, create=True)
        ua = UserAddr(user=self, addr=addr)
        self.addrs.append(ua)
        db.Session.add(self)
        return ua

    @staticmethod
    async def addr_del(db, user_pk: int, address: str) -> Optional[AttrDict]:
        return await db.run_in_executor_session(User._addr_del, db, user_pk, address)

    @staticmethod
    def _addr_del(db, user_pk: int, address: str) -> Optional[AttrDict]:
        addr = Addr._load(db, address, create=False)

        stmt = UserAddr.__table__.delete().where(
            and_(
                UserAddr.user_pk == user_pk,
                UserAddr.addr_pk == addr.pkid
            )
        )

        rows_found = db.Session.execute(stmt).rowcount

        if rows_found > 0:
            if not len(addr.users):
                if not len(addr.info):
                    log.info(f"Deleting address with no users and empty info: {str(addr)}")
                    db.Session.delete(addr)
                else:
                    log.info(f"Keeping address with no users and non-empty info: {str(addr)}")

            db.Session.commit()
            return AttrDict(addr.asdict())


