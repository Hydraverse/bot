from sqlalchemy.orm import declarative_base

__all__ = "Base", "dictattrs"

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
