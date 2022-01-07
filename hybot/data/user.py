from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy_json import NestedMutableJson

from .base import Base, dictattrs

__all__ = "User",


@dictattrs("user_id", "date_create", "date_update", "info", "data", "addrs", "tokns")
class User(Base):
    __tablename__ = "user"
    __mapper_args__ = {"eager_defaults": True}

    user_id = Column(Integer, nullable=False, primary_key=True, index=True)

    date_create = Column(DateTime, default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, onupdate=func.now(), index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})

    addrs = relationship("Addr", secondary="user_addr", back_populates="users", cascade="all, delete")
    tokns = relationship("Tokn", secondary="user_tokn", back_populates="users", cascade="all, delete")
