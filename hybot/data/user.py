from attrdict import AttrDict
from sqlalchemy import Column, Integer
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import relationship, lazyload

from .base import *

__all__ = "User",


@dictattrs("pkid", "date_create", "date_update", "user_id", "info", "data", "addrs", "tokns")
class User(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "user"

    user_id = Column(Integer, nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    addrs = relationship("Addr", secondary="user_addr", back_populates="users", cascade="all, delete")
    tokns = relationship("Tokn", secondary="user_tokn", back_populates="users", cascade="all, delete")

    @staticmethod
    async def load_or_create(db, user_id: int, full: bool = False) -> AttrDict:
        return await db.run_in_executor_session(User._load_or_create, db, user_id, full)

    @staticmethod
    def _load_or_create(db, user_id: int, full: bool) -> AttrDict:
        try:
            # noinspection PyProtectedMember
            return AttrDict(
                db.Session.query(
                    User.pkid, User.user_id, User.info, User.data
                ).filter(
                    User.user_id == user_id
                ).one()._asdict()
                if not full else
                db.Session.query(
                    User
                ).filter(
                    User.user_id == user_id
                ).one().asdict()
            )

        except NoResultFound:
            user_ = User(user_id=user_id)

            db.Session.add(user_)
            db.Session.commit()

            return AttrDict(user_.asdict())

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
            lazyload(User.tokns)
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
        return await db.run_in_executor_session(User._delete, user_id)

    @staticmethod
    def _delete(db, user_id: int) -> None:
        u: User = db.Session.query(User).where(
            User.user_id == user_id
        ).options(
            lazyload(User.tokns)
        ).one()

        from . import UserAddr
        UserAddr._remove_addrs(db, u)
        db.Session.delete(u)
        db.Session.commit()

