import os
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select as future_select
from aiogram.types.user import User as TelegramUser
from attrdict import AttrDict
import asyncio

from . import *
from hydra import log

__all__ = "DB",


class DB:
    engine = None
    Session = None

    FILE_DIR = "local"
    FILE_NAME = "hybot"
    PATH = os.path.abspath(os.path.join(os.getcwd(), f"{FILE_DIR}/{FILE_NAME}.sqlite3"))

    def __init__(self, url, *args, **kwds):
        log.debug(f"db: open url='{url}'")
        self.engine = create_engine(url, *args, **kwds)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        Base.metadata.create_all(self.engine)

    @staticmethod
    def default():
        return DB(f"sqlite:///{DB.PATH}")  # , echo=log.level() <= log.INFO)

    async def user_load_or_create(self, tg_user: TelegramUser) -> AttrDict:
        return await asyncio.get_event_loop().run_in_executor(None, self._user_load_or_create, tg_user)

    def _user_load_or_create(self, tg_user: TelegramUser) -> AttrDict:
        self.Session()

        try:
            return AttrDict(self.Session.execute(User.from_tgid(tg_user.id)).scalar_one().asdict())

        except sqlalchemy.exc.NoResultFound:
            user_ = User(
                tgid=tg_user.id,
                name=tg_user.first_name or tg_user.username
            )

            # noinspection PyBroadException
            try:
                self.Session.add(user_)
                self.Session.commit()

            except BaseException:
                self.Session.rollback()
                raise

            return AttrDict(user_.asdict())

        finally:
            self.Session.remove()

    async def user_info_update(self, tg_user: TelegramUser, info: dict) -> None:
        return await asyncio.get_event_loop().run_in_executor(None, self._user_info_update, tg_user, info)

    def _user_info_update(self, tg_user: TelegramUser, info: dict) -> None:
        self.Session()

        try:
            u = self.Session.execute(User.from_tgid(tg_user.id)).scalar_one()
            u.info.update(info)

            self.Session.add(u)
            self.Session.commit()

        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise

        finally:
            self.Session.remove()
