from sqlalchemy import Column, ForeignKey, Integer, String

from hybot.data.base import *
from hybot.util import namegen

__all__ = "UserPkid",


@dictattrs("pkid", "name")
class UserPkid(DbPkidMixin, Base):
    __tablename__ = "user_pkid"

    name = Column(String, default=lambda: UserPkid.make_name(), nullable=False, unique=True, index=True)

    @staticmethod
    def make_name():
        return " ".join(namegen.make_name())


class DbUserPkidMixin:

    pkid = lambda: Column(Integer, ForeignKey("user_pkid.pkid"), nullable=False, unique=True, primary_key=True, index=True)
    name = lambda: Column(String, ForeignKey("user_pkid.name"), nullable=False, unique=True, primary_key=True, index=True)
