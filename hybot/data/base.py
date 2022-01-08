from sqlalchemy import Column, DateTime, func, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy_json import NestedMutableJson

__all__ = (
    "Base", "dictattrs",
    "DbPkidMixin", "DbDateMixin",
    "DbInfoColumn", "DbDataColumn",
)

Base = declarative_base()


def dictattrs(*attrs):
    def _asdict(self):
        return {
            attr: getattr(self, attr)
            for attr in attrs
        }

    def _cls(cls):
        cls.asdict = _asdict
        return cls

    return _cls


DbInfoColumn = lambda: Column(NestedMutableJson, nullable=False, index=True, default={})
DbDataColumn = lambda: Column(NestedMutableJson, nullable=False, index=False, default={})


class DbPkidMixin:
    pkid = Column(Integer, nullable=False, unique=True, primary_key=True, autoincrement=True, index=True)


class DbDateMixin:
    __mapper_args__ = {"eager_defaults": True}

    date_create = Column(DateTime, default=func.now(), nullable=False, index=True)
    date_update = Column(DateTime, onupdate=func.now(), index=True)




