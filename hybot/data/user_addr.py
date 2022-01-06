from sqlalchemy import Column, Table
from sqlalchemy import ForeignKey
from sqlalchemy import Integer

from hybot.data.base import Base


UserAddr = Table(
    "user_addr", Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True, index=True),
    Column("addr_id", Integer, ForeignKey("addr.id"), primary_key=True, index=True)
)
