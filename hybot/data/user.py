from __future__ import annotations
from typing import Optional

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, Integer, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, lazyload

from .base import *
from .db import DB
from .addr import Addr
from .user_pkid import UserPkid, DbUserPkidMixin
from .user_addr import UserAddr

__all__ = "User", "UserPkid", "UserAddr",


@dictattrs("pkid", "name", "user_id", "date_create", "date_update", "info", "data")
class User(DbUserPkidMixin, DbDateMixin, Base):
    __tablename__ = "user"

    pkid = DbUserPkidMixin.pkid()
    name = DbUserPkidMixin.name()

    user_id = Column(Integer, nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    user_addrs = relationship(
        UserAddr,
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    def __str__(self):
        return f"{self.pkid} [{self.name}] {self.user_id}"

    def attrdict(self, full=False):
        user_dict = AttrDict(self.asdict())

        if full:
            user_dict.user_addrs = list(
                AttrDict(
                    user=ua.user.asdict(),
                    addr=ua.addr.asdict(),
                )
                for ua in self.user_addrs
            )

        return user_dict

    @staticmethod
    async def get_pkid(db: DB, user_id: int) -> Optional[int]:
        return await db.run_in_executor_session(User._get_pkid, db, user_id)

    @staticmethod
    def _get_pkid(db: DB, user_id: int) -> Optional[int]:
        u = (
            db.Session.query(
                User.pkid
            ).filter(
                User.user_id == user_id
            ).one_or_none()
        )

        return u.pkid if u is not None else None

    @staticmethod
    async def get(db: DB, user_id: int, create: bool = True, full: bool = False) -> Optional[AttrDict]:
        return await db.run_in_executor_session(User._get, db, user_id, create, full)

    @staticmethod
    def _get(db: DB, user_id: int, create: bool, full: bool) -> Optional[AttrDict]:

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
    async def update_info(db: DB, user_pk: int, info: dict, data: dict = None, over: bool = False) -> None:
        if (info is None and data is None) or (over and (not info or not data)):
            return
        return await db.run_in_executor_session(User._update_info, db, user_pk, info, data, over)

    @staticmethod
    def _update_info(db: DB, user_pk: int, info: dict, data: dict, over: bool) -> None:
        u: User = db.Session.query(User).where(
            User.pkid == user_pk
        ).options(
            lazyload(User.user_addrs)
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
    async def delete(db: DB, user_id: int) -> None:
        return await db.run_in_executor_session(User.__delete, db, user_id)

    @staticmethod
    def __delete(db: DB, user_id: int) -> None:
        u: User = db.Session.query(User).where(
            User.user_id == user_id
        ).one_or_none()

        if u is not None:
            return u._delete(db)
        
    def _delete(self, db: DB):
        for user_addr in list(self.user_addrs):
            user_addr._remove(db, self.user_addrs)

        db.Session.delete(self)
        db.Session.commit()

    @staticmethod
    async def addr_add(db: DB, user_pk: int, address: str) -> AttrDict:
        return await db.run_in_executor_session(User._addr_add, db, user_pk, address)

    @staticmethod
    def _addr_add(db: DB, user_pk: int, address: str) -> AttrDict:
        u: User = db.Session.query(
            User
        ).where(
            User.pkid == user_pk
        ).options(
            lazyload(User.user_addrs)
        ).one()

        user_addr: UserAddr = u.__addr_add(db, address)
        db.Session.commit()
        return AttrDict(user=user_addr.user.asdict(), addr=user_addr.addr.asdict())

    def __addr_add(self, db, address: str) -> UserAddr:
        addr = Addr.get(db, address, create=True)
        ua = UserAddr(user=self, addr=addr)
        db.Session.add(ua)
        return ua

    @staticmethod
    async def addr_del(db: DB, user_pk: int, address: str) -> Optional[AttrDict]:
        return await db.run_in_executor_session(User._addr_del, db, user_pk, address)

    @staticmethod
    def _addr_del(db: DB, user_pk: int, address: str) -> Optional[AttrDict]:
        addr = Addr.get(db, address, create=False)

        if addr is not None:
            ua: UserAddr = db.Session.query(
                UserAddr,
            ).where(
                and_(
                    UserAddr.user_pk == user_pk,
                    UserAddr.addr_pk == addr.pkid,
                )
            ).one_or_none()

            if ua is not None:
                addr_dict = addr.asdict()
                ua._remove(db, ua.user.user_addrs)
                db.Session.commit()
                return AttrDict(addr_dict)
