import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import *
from hydra import log

__all__ = "DB",


class DB:
    engine = None
    session = None
    Session = None

    FILE_DIR = "local"
    FILE_NAME = "hybot"
    PATH = os.path.abspath(os.path.join(os.getcwd(), f"{FILE_DIR}/{FILE_NAME}.sqlite3"))

    def __init__(self, url, *args, **kwds):
        log.debug(f"db: open url='{url}'")
        self.engine = create_engine(url, *args, **kwds)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        Base.metadata.create_all(self.engine)

    @staticmethod
    def default():
        return DB(f"sqlite:///{DB.PATH}", echo=log.level() <= log.INFO)


    def user_by_tgid(self):
        return future_select()