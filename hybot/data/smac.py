from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from .base import *

__all__ = "Smac",


@dictattrs("pkid", "date_create", "date_update", "smac_id", "info", "data", "users")
class Smac(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "smac"

    smac_id = Column(String(40), nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    users = relationship("User", secondary="user_smac", back_populates="smacs", passive_deletes=True)
