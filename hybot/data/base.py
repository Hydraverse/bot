from attrdict import AttrDict
from sqlalchemy import Column, DateTime, func, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy_json import NestedMutableJson

__all__ = (
    "Base", "dictattrs",
    "DbPkidMixin", "DbDateMixin",
    "DbInfoColumn", "DbDataColumn",
    "DbUserDataMixin",
)


def dictattrs(*attrs):
    def _asdict(self, attrs_) -> AttrDict:
        def _attr_conv(s, attr):
            attr = getattr(s, attr)
            if hasattr(attr, "_asdict"):
                return attr._asdict()
            if isinstance(attr, (list, tuple)):
                return [_attr_conv(attr, a) for a in attr]
            return attr

        return AttrDict({
            attr: _attr_conv(self, attr)
            for attr in attrs_
        })

    def _cls(cls):
        cls.__dictattrs__ = getattr(cls, "__dictattrs__", ()) + attrs
        cls._asdict = lambda slf, *atrs_: _asdict(slf, tuple(cls.__dictattrs__) + atrs_)

        return cls

    return _cls


class Base:
    def asdict(self) -> AttrDict:
        return getattr(self, "_asdict", AttrDict)()


Base = declarative_base(cls=Base)

DbInfoColumn = lambda: Column(NestedMutableJson, nullable=False, index=True, default={})
DbDataColumn = lambda: Column(NestedMutableJson, nullable=False, index=False, default={})


class DbPkidMixin:
    __mapper_args__ = {"eager_defaults": True}

    pkid = Column(Integer, nullable=False, unique=True, primary_key=True, autoincrement=True, index=True)


class DbDateMixin:
    __mapper_args__ = {"eager_defaults": True}

    date_create = Column(DateTime, default=func.now(), nullable=False, index=False)
    date_update = Column(DateTime, onupdate=func.now(), index=True)


class DbUserDataMixin:
    user_data = DbDataColumn

    def user_data_for(self, key: int, default: AttrDict = None) -> AttrDict:
        if default is None:
            default = AttrDict()
        return self.user_data.setdefault(key, default)

    def user_data_del(self, key: int) -> None:
        if key in self.user_data:
            del self.user_data[key]


