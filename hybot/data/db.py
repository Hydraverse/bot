import os
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import asyncio

from hydra.rpc import HydraRPC
from hydra import log

from .base import Base

__all__ = "DB",


class DbOperatorMixin:
    @staticmethod
    async def run_in_executor(fn, *args):
        return await asyncio.get_event_loop().run_in_executor(None, fn, *args)

    async def run_in_executor_session(self, fn, *args):
        return await DB.run_in_executor(lambda: self._run_in_executor_session(fn, *args))

    def _run_in_executor_session(self, fn, *args):
        raise NotImplementedError


# noinspection PyProtectedMember
class DB(DbOperatorMixin):
    engine = None
    Session = None  # type: scoped_session
    rpc: HydraRPC = None

    FILE_DIR = "local"
    FILE_NAME = "hybot"
    PATH = os.path.abspath(os.path.join(os.getcwd(), f"{FILE_DIR}/{FILE_NAME}.sqlite3"))

    def __init__(self, rpc: HydraRPC, url: str, *args, **kwds):
        log.debug(f"db: open url='{url}'")
        self.engine = create_engine(url, *args, **kwds)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        Base.metadata.create_all(self.engine)
        self.rpc = rpc

    @staticmethod
    def default(rpc: HydraRPC):
        return DB(rpc, f"sqlite:///{DB.PATH}")  # , echo=log.level() <= log.INFO)

    def _run_in_executor_session(self, fn, *args):
        self.Session()

        try:
            return fn(*args)
        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise
        finally:
            self.Session.remove()
