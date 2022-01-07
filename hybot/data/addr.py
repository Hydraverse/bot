from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.orm import relationship

from .base import Base, dictattrs

__all__ = "Addr",


@dictattrs("addr_id", "date_create", "date_update", "info", "data", "users")
class Addr(Base):
    __tablename__ = "addr"
    __mapper_args__ = {"eager_defaults": True}

    addr_id = Column(String(34), nullable=False, primary_key=True, index=True)

    date_create = Column(DateTime, default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, onupdate=func.now(), index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})

    users = relationship("User", secondary="user_addr", back_populates="addrs", passive_deletes=True)
