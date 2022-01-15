from __future__ import annotations

import os
from typing import Dict

import sqlalchemy.exc
from hydra.rpc.base import BaseRPC
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import asyncio

from hydra.rpc import HydraRPC
from hydra import log


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
    _: Dict[HydraRPC, DB] = {}
    engine = None
    Session = None  # type: scoped_session
    rpc: HydraRPC = None

    FILE_DIR = "local"
    FILE_NAME = "hybot"
    FILE_PATH = os.path.abspath(os.path.join(os.getcwd(), f"{FILE_DIR}/{FILE_NAME}.sqlite3"))

    WALLET = "hybot"

    def __init__(self, rpc: HydraRPC, url: str, *args, **kwds):
        log.debug(f"db: open url='{url}'")
        self.engine = create_engine(url, *args, **kwds)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        Base.metadata.create_all(self.engine)
        self.rpc = rpc
        self.__init_wallet()

    def __hash__(self):
        return hash(self.FILE_PATH + self.rpc.url)

    def __init_wallet(self):
        if DB.WALLET is not None and DB.WALLET not in self.rpc.listwallets():
            try:
                log.info(f"Loading wallet '{DB.WALLET}'...")
                self.rpc.loadwallet(DB.WALLET)
                log.info(f"Wallet '{DB.WALLET}' loaded.")
            except BaseRPC.Exception:
                log.warning(f"Creating wallet '{DB.WALLET}'...")
                self.rpc.createwallet(DB.WALLET, disable_private_keys=True, blank=True)
                log.warning(f"Wallet '{DB.WALLET}' created.")

    @staticmethod
    def default(rpc: HydraRPC):
        if rpc not in DB._:
            return DB._.setdefault(rpc, DB(rpc, f"sqlite:///{DB.FILE_PATH}"))  # , echo=log.level() <= log.INFO)

        return DB._[rpc]

    def _run_in_executor_session(self, fn, *args):
        self.Session()

        try:
            return fn(*args)
        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise
        finally:
            self.Session.remove()


if DB.WALLET is not None:
    os.environ.setdefault("HY_RPC_WALLET", DB.WALLET)


from .base import __all__ as __base_all__
from .base import *
from .user import __all__ as __user_all__
from .user import *
from .addr import __all__ as __addr_all__
from .addr import *
from .block import __all__ as __block_all__
from .block import *
from .tx import __all__ as __tx_all__
from .tx import *

__all__ = ("DB",) + \
          __base_all__ + \
          __user_all__ + \
          __addr_all__ + \
          __block_all__ + \
          __tx_all__
