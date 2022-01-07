from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.orm import relationship

from .base import Base, dictattrs

__all__ = "Tokn",


@dictattrs("tokn_id", "date_create", "date_update", "info", "data", "users")
class Tokn(Base):
    __tablename__ = "tokn"
    __mapper_args__ = {"eager_defaults": True}

    tokn_id = Column(String(40), nullable=False, primary_key=True, index=True)

    date_create = Column(DateTime, default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, onupdate=func.now(), index=True)

    info = Column(NestedMutableJson, nullable=False, index=True, default={})
    data = Column(NestedMutableJson, nullable=False, index=False, default={})

    users = relationship("User", secondary="user_tokn", back_populates="tokns", passive_deletes=True)
