import os
from typing import Optional

import sqlalchemy.exc
from attrdict import AttrDict
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from aiogram.types.user import User as TelegramUser

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
        return DB(f"sqlite:///{DB.PATH}", echo=log.level() <= log.INFO)

    def user_load_or_create(self, tg_user: TelegramUser) -> User:
        self.Session()

        try:
            # noinspection PyProtectedMember
            return self.Session.execute(User.from_tgid(tg_user.id)).scalar_one()

        except sqlalchemy.exc.NoResultFound:
            self.Session.rollback()

            user_ = User(
                tgid=tg_user.id,
                name=tg_user.username,
            )

            # noinspection PyBroadException
            try:
                self.Session.add(user_)
                self.Session.commit()

            except BaseException:
                self.Session.rollback()
                raise

            return user_

        finally:
            self.Session.remove()
