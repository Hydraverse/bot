from sqlalchemy import Column, ForeignKey
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.orm import relationship

from .base import Base

__all__ = "Tokn",


class Tokn(Base):
    __tablename__ = "tokn"

    # required in order to access columns with server defaults
    # or SQL expression defaults, after a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}

    tokn_id = Column(Integer, unique=True, primary_key=True, autoincrement=True, index=True)

    address = Column(String, nullable=False, unique=True, index=True)

    date_create = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False, index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})

    users = relationship("User", secondary="user_tokn", back_populates="tokns", passive_deletes=True)

