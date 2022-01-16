from sqlalchemy import Column, ForeignKey, Integer, String, BigInteger
from time import time_ns

from sqlalchemy.orm import relationship, declared_attr

from hybot.data.base import *
from .db import DB
from hybot.util import namegen

__all__ = "UserUniq",


@dictattrs("pkid", "date_create", "date_update", "name", "time", "nano", "info", "data")
class UserUniq(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "user_uniq"

    name = Column(String, nullable=False, unique=True)
    time = Column(BigInteger, nullable=False, unique=True)
    nano = Column(BigInteger, nullable=False, unique=False)

    # addr_shr_hy = Column(String(34), nullable=False, unique=True)
    # addr_shr_pk = Column(String(52), nullable=False, unique=True)
    # addr_loc_hy = Column(String(34), nullable=False, unique=True)
    # addr_loc_pk = Column(String(52), nullable=False, unique=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    # noinspection PyUnusedLocal
    def __init__(self, db: DB):
        ts_ns = td_ns = time_ns()
        name = " ".join(namegen.make_name())
        td_ns = time_ns() - td_ns
        super().__init__(name=name, time=ts_ns, nano=td_ns)

    @staticmethod
    def make_name():
        return " ".join(namegen.make_name())


class DbUserUniqMixin:

    @declared_attr
    def pkid(self):
        return Column(Integer, ForeignKey("user_uniq.pkid", ondelete="CASCADE"), nullable=False, unique=True, primary_key=True, index=True)

    # name = Column(String, ForeignKey("user_uniq.name"), nullable=False, unique=True, primary_key=True, index=True)

    @declared_attr
    def uniq(self):
        return relationship("UserUniq")
