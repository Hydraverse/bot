from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from .base import *

__all__ = "Tokn",


@dictattrs("id", "date_create", "date_update", "tokn_id", "info", "data", "users")
class Tokn(DbIdMixin, DbDateMixin, Base):
    __tablename__ = "tokn"

    tokn_id = Column(String(40), nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    users = relationship("User", secondary="user_tokn", back_populates="tokns", passive_deletes=True)
