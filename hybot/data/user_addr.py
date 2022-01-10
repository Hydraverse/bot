from typing import Tuple, List

from attrdict import AttrDict
from hydra import log
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import lazyload

from hybot.data import Addr, User
from hybot.data.base import *

__all__ = "UserAddr",


@dictattrs("user_pk", "addr_pk", "date_create", "date_update", "info", "data")
class UserAddr(DbDateMixin, Base):
    __tablename__ = "user_addr"

    user_pk = Column(Integer, ForeignKey("user.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    addr_pk = Column(Integer, ForeignKey("addr.pkid", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)

    info = DbInfoColumn()
    data = DbDataColumn()

    @staticmethod
    async def add(db, user_pk: int, address: str) -> Tuple[int, Addr.Type, str, str, AttrDict]:
        """Add address. Returns tuple (pkid, type, id_int, hydra_str)
        """
        return await db.run_in_executor_session(UserAddr._add, db, user_pk, address)

    @staticmethod
    def _add(db, user_pk: int, address: str) -> Tuple[int, Addr.Type, str, str, AttrDict]:

        addr_tp, addr_hx, addr_hy = Addr._addr_normalize(db, address)

        addr_info = AttrDict()

        try:
            addr_: Addr = db.Session.query(Addr).where(
                Addr.addr_hx == addr_hx
            ).options(
                lazyload(Addr.users)
            ).one()

        except NoResultFound:
            if addr_tp == Addr.Type.S:
                addr_tp, sc_info = Addr._validate_contract(db, addr_hx)

                if len(sc_info):
                    addr_info.sc = sc_info

            addr_: Addr = Addr(
                addr_tp=addr_tp,
                addr_hx=addr_hx,
                addr_hy=addr_hy,
                info=addr_info
            )

        u = db.Session.query(User).where(User.pkid == user_pk).options(
            lazyload(User.addrs)
        ).one()

        u.addrs.append(addr_)
        db.Session.add(u)
        db.Session.commit()

        return (
            addr_.pkid,
            addr_.addr_tp,
            addr_.addr_hx,
            addr_.addr_hy,
            AttrDict(addr_.info)
        )

    @staticmethod
    async def load_all(db) -> List[AttrDict]:
        return await db.run_in_executor_session(UserAddr._load_all, db)

    @staticmethod
    def _load_all(db) -> List[AttrDict]:
        return list(map(lambda ua: ua.asdict(), db.Session.query(UserAddr)))

    @staticmethod
    async def load(db, user_pk: int, addr_pk: int) -> AttrDict:
        return await db.run_in_executor_session(UserAddr._load, db, user_pk, addr_pk)

    @staticmethod
    def _load(db, user_pk: int, addr_pk: int) -> AttrDict:
        return AttrDict(db.Session.query(UserAddr).where(
            UserAddr.user_pk == user_pk and
            UserAddr.addr_pk == addr_pk
        ).one().asdict())

    @staticmethod
    async def update(
            db, user_pk: int, addr_pk: int,
            info: dict, data: dict = None, over: bool = False) -> None:
        if (info is None and data is None) or (over and (not info or not data)):
            return

        return await db.run_in_executor_session(UserAddr._update, db, user_pk, addr_pk, info, data, over)

    @staticmethod
    def _update(db, user_pk: int, addr_pk: int, info: dict, data: dict, over: bool) -> None:
        ua: UserAddr = db.Session.query(UserAddr).where(
            UserAddr.user_pk == user_pk and
            UserAddr.addr_pk == addr_pk
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

        db.Session.add(ua)
        db.Session.commit()

    @staticmethod
    async def remove(db, user_pk: int, addr_pk: int) -> None:
        return await db.run_in_executor_session(UserAddr._remove, db, user_pk, addr_pk)

    @staticmethod
    def _remove(db, user_pk: int, addr_pk: int) -> None:
        # TODO: Determine how to properly filter .addrs while still returning a single User row.
        u: User = db.Session.query(
            User
        ).where(
            User.pkid == user_pk
        ).options(
            lazyload(User.addrs)  # TODO: Evaluate how this affects loop below
        ).one()

        for addr_ in u.addrs:
            if addr_.pkid == addr_pk:
                break
        else:
            return

        UserAddr._remove_addrs(db, u, addr_)
        db.Session.commit()

    @staticmethod
    def _remove_addrs(db, u: User, addr_rm: Addr = None) -> None:
        for addr_ in u.addrs:
            if addr_rm is not None and addr_ is not addr_rm:
                continue

            u.addrs.remove(addr_)

            if not len(addr_.users):
                log.info(f"DB: no users remain for #{addr_.pkid}")

                if not len(addr_.info):
                    log.info("DB: deleting addr with no users and empty info")
                    db.Session.delete(addr_)
                    continue

        db.Session.add(u)

    @staticmethod
    async def update_txns(db, process_user_addr_txs_func=None) -> List:
        return await db.run_in_executor_session(UserAddr._update_txns, db, process_user_addr_txs_func)

    @staticmethod
    def _update_txns(db, process_user_addr_txs_func) -> List:
        """Scan all entries and update to the latest tx for each."""
        # addr_pks = db.Session.query(UserAddr.addr_pk).distinct(UserAddr.addr_pk)
        user_addrs = db.Session.query(UserAddr).all()
        addr_pks = set(ua.addr_pk for ua in user_addrs)
        user_pks = set()

        for addr_pk in addr_pks:
            addr_ = db.Session.query(Addr).where(Addr.pkid == addr_pk).one()

            if addr_.addr_tp != Addr.Type.H:
                continue

            addr_._ensure_imported(db)

            tx_data = addr_.data.setdefault("tx", {"prev": None, "cur": None})

            tx_latest = db.rpc.listtransactions(addr_.addr_hy, count=1, skip=0, include_watchonly=True)

            if tx_latest is not None and len(tx_latest):
                tx_latest = tx_latest[0]

                if tx_latest.txid not in tx_data:
                    tx_data.clear()
                    tx_data[tx_latest.txid] = tx_latest
                    db.Session.add(addr_)

                    for user_addr in filter(lambda ua: ua.addr_pk == addr_pk, user_addrs):
                        ua_txs = user_addr.data.setdefault("tx", {})

                        if tx_latest.txid not in ua_txs:
                            # Remove cleared txes
                            for txid in filter(lambda k: ua_txs[k] is None, ua_txs.keys()):
                                del ua_txs[txid]

                            user_pks.add(user_addr.user_pk)
                            ua_txs[tx_latest.txid] = tx_latest
                            db.Session.add(user_addr)

                            if process_user_addr_txs_func is not None:
                                for user_ in addr_.users:
                                    if user_.pkid == user_addr.user_pk:
                                        process_user_addr_txs_func(db, user_, ua_txs)

                    db.Session.commit()

        return list(user_pks)



