from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship

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
