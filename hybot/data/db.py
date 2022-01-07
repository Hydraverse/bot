import os
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from attrdict import AttrDict
import asyncio

from . import *
from hydra.rpc import HydraRPC
from hydra import log

__all__ = "DB",


class DB:
    engine = None
    Session = None
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

    @staticmethod
    async def run_in_executor(func, *args):
        return await asyncio.get_event_loop().run_in_executor(None, func, *args)

    # BEGIN - ETL
    #

    async def validate_address(self, address: str):
        return await DB.run_in_executor(self.validate_address_, address)

    def validate_address_(self, address: str):
        return self.rpc.validateaddress(address).isvalid

    async def user_load_or_create(self, user_id: int) -> AttrDict:
        return await DB.run_in_executor(self.user_load_or_create_, user_id)

    def user_load_or_create_(self, user_id: int) -> AttrDict:
        self.Session()

        try:
            return AttrDict(self.Session.query(User).where(
                User.user_id == user_id
            ).one().asdict())

        except sqlalchemy.exc.NoResultFound:
            user_ = User(user_id=user_id)

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

    async def user_update_info(self, user_id: int, info: dict, data: dict = None, over: bool = False) -> None:
        if (info is None and data is None) or (over and (not info or not data)):
            return
        return await DB.run_in_executor(self.user_update_info_, user_id, info, data, over)

    def user_update_info_(self, user_id: int, info: dict, data: dict, over: bool) -> None:
        self.Session()

        try:
            u: User = self.Session.query(User).where(
                User.user_id == user_id
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

            self.Session.add(u)
            self.Session.commit()

        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise

        finally:
            self.Session.remove()

    async def user_addr_load(self, user_id: int, addr_id: str) -> AttrDict:
        return await DB.run_in_executor(self.user_addr_load_, user_id, addr_id)

    def user_addr_load_(self, user_id: int, addr_id: str) -> AttrDict:
        self.Session()

        try:
            if not self.rpc.validateaddress(addr_id).isvalid:
                raise ValueError(f"Invalid HYDRA address '{addr_id}'")

            try:
                return AttrDict(self.Session.query(UserAddr).where(
                    UserAddr.user_id == user_id and
                    UserAddr.addr_id == addr_id
                ).one().asdict())

            except sqlalchemy.exc.NoResultFound:
                user_: User = self.Session.query(User).where(
                    User.user_id == user_id
                ).one()

                try:
                    addr_: Addr = self.Session.query(Addr).where(
                        Addr.addr_id == user_id
                    ).one()
                except sqlalchemy.exc.NoResultFound:
                    addr_: Addr = Addr(addr_id=addr_id)

                user_.addrs.append(addr_)

                self.Session.add(user_)
                self.Session.commit()

                return AttrDict(user_.asdict())

        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise

        finally:
            self.Session.remove()

    async def user_addr_update(
            self, user_id: int, addr_id: str,
            info: dict, data: dict = None, over: bool = False
    ) -> None:
        if (info is None and data is None) or (over and (not info or not data)):
            return

        return await DB.run_in_executor(self.user_addr_update_, user_id, addr_id, info, data, over)

    def user_addr_update_(self, user_id: int, addr_id: str, info: dict, data: dict, over: bool) -> None:
        self.Session()

        try:
            ua: UserAddr = self.Session.query(UserAddr).where(
                UserAddr.user_id == user_id and
                UserAddr.addr_id == addr_id
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

            self.Session.add(ua)
            self.Session.commit()

        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise

        finally:
            self.Session.remove()

    async def user_addr_remove(self, user_id: int, addr_id: str) -> None:
        return await DB.run_in_executor(self.user_addr_remove_, user_id, addr_id)

    def user_addr_remove_(self, user_id: int, addr_id: str) -> None:
        self.Session()

        try:
            self.Session.query(UserAddr).where(
                UserAddr.user_id == user_id and
                UserAddr.addr_id == addr_id
            ).delete()

            self.Session.commit()

        except sqlalchemy.exc.SQLAlchemyError:
            self.Session.rollback()
            raise

        finally:
            self.Session.remove()
