"""Created by Halospace Foundation.
Support: t.me/TheHydraverse
"""
from __future__ import annotations
from aiogram import Bot, Dispatcher, types
from attrdict import AttrDict

from hydra.rpc import HydraRPC
from hybot.data import *
from hybot.conf import Config

CONF = {
    "token": "(bot token from @BotFather)",
    "donations": "HUo97u33iEdkEWBiLZEitAsGRXHUcmdfHQ"
}


@Config.defaults(CONF)
class HydraBot(Bot):
    _: HydraBot = None
    __DP = Dispatcher()

    rpc: HydraRPC = None
    conf: AttrDict = None
    db: DB = None

    def __new__(cls, *args, **kwargs):
        if cls._ is None:
            cls._ = super(HydraBot, cls).__new__(cls, *args, **kwargs)

        return cls._

    def __init__(self, rpc: HydraRPC):
        self.rpc = rpc
        self.conf = Config.get(HydraBot)
        self.db = DB.default(self.rpc)

        token = self.conf.get("token", None)

        if not token:
            raise ValueError("Invalid or no token found in config")

        from . import \
            hello as cmd_hello,\
            nick as cmd_nick,\
            tz as cmd_tz,\
            addr as cmd_addr,\
            delete as cmd_delete

        @HydraBot.__DP.message(commands={"hello"})
        async def hello(msg: types.Message):
            return await cmd_hello.hello(self, msg)

        @HydraBot.__DP.message(commands={"nick"})
        async def nick(msg: types.Message):
            return await cmd_nick.nick(self, msg)

        @HydraBot.__DP.message(commands={"tz"})
        async def tz(msg: types.Message):
            return await cmd_tz.tz(self, msg)

        @HydraBot.__DP.message(commands={"addr"})
        async def addr_(msg: types.Message):
            return await cmd_addr.addr(self, msg)

        @HydraBot.__DP.message(commands={"DELETE"})
        async def delete(msg: types.Message):
            return await cmd_delete.delete(self, msg)

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(rpc: HydraRPC):
        return HydraBot(rpc).run()

    @staticmethod
    @__DP.message(commands={"echo"})
    async def echo(msg: types.Message):
        return await msg.reply(msg.text)

    def run(self):
        return HydraBot.__DP.run_polling(self)
