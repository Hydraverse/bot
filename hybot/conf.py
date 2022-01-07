import os
import yaml
from attrdict import AttrDict

from hydra import log


class Config:
    ENV_BASE = "HYBOT_HOME"
    APP_NAME = "hybot"
    APP_FILE = "conf.yaml"
    DIR_APPS = ".local"

    DIR_BASE = os.path.abspath(os.getenv(ENV_BASE, os.getenv("HOME", os.getcwd())))
    APP_BASE = os.path.join(DIR_BASE, DIR_APPS, APP_NAME)
    APP_CONF = os.path.join(APP_BASE, APP_FILE)

    DEFAULT = AttrDict()

    @staticmethod
    def get(cls: type) -> AttrDict:
        return AttrDict(Config.read(create=True).get(
            cls.__name__, Config.DEFAULT.get(cls.__name__, None)
        ))

    @staticmethod
    def set(cls: type, data: dict) -> None:
        curr_data = Config.read(create=True)
        curr_data[cls.__name__] = data
        Config.write(curr_data)

    @staticmethod
    def defaults(data: dict = None):

        if data is None:
            data = AttrDict()

        def default(cls: type):
            Config.DEFAULT[cls.__name__] = data
            return cls

        return default

    @staticmethod
    def exists() -> bool:
        return os.path.isfile(Config.APP_CONF)

    @staticmethod
    def read(create: bool = False) -> AttrDict:

        if not Config.exists():
            if not create:
                raise FileNotFoundError(Config.APP_CONF)

            Config.write(Config.DEFAULT, create=True)
            return Config.DEFAULT

        with open(Config.APP_CONF, "r") as conf:
            return AttrDict(yaml.safe_load(conf))

    @staticmethod
    def write(data: dict, create: bool = True) -> None:
        if not Config.exists():
            if not create:
                raise FileNotFoundError(Config.APP_CONF)

            log.debug(f"create: {Config.APP_CONF}")
            os.makedirs(Config.APP_BASE, exist_ok=True)

        with open(Config.APP_CONF, "w") as conf:
            yaml.dump(dict(data), conf)

