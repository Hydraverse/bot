from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from .base import *

__all__ = "Addr",


@dictattrs("pkid", "date_create", "date_update", "addr_id", "info", "data", "users")
class Addr(DbPkidMixin, DbDateMixin, Base):
    __tablename__ = "addr"

    addr_id = Column(String(42), nullable=False, unique=True, primary_key=False, index=True)

    info = DbInfoColumn()
    data = DbDataColumn()

    users = relationship("User", secondary="user_addr", back_populates="addrs", passive_deletes=True)

    @staticmethod
    async def validate_address(db, address: str):
        return await type(db).run_in_executor(Addr._validate_address, db, address)

    @staticmethod
    def _validate_address(db, address: str):
        return db.rpc.validateaddress(address)
