from __future__ import annotations
from aiogram import Bot, Dispatcher, types
from attrdict import AttrDict

from hydra.rpc import HydraRPC

from ..conf import Config

CONF = {
    "token": "(bot token from @BotFather)",
    "donations": "(developer address to shill for donations)"
}


def singletonmethod(func):
    return lambda *a, **k: HydraBot.call(func, *a, **k)


@Config.defaults(CONF)
class HydraBot(Bot):
    __HydraBot: HydraBot = None
    __DP = Dispatcher()

    rpc: HydraRPC = None
    conf: AttrDict = None

    def __new__(cls, *args, **kwargs):
        if cls.__HydraBot is None:
            cls.__HydraBot = super(HydraBot, cls).__new__(cls, *args, **kwargs)

        return cls.__HydraBot

    def __init__(self, rpc: HydraRPC):
        self.rpc = rpc
        self.conf = Config.get(HydraBot)

        token = self.conf.get("token", None)

        if not token:
            raise ValueError("Invalid or no token found in config")

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def call(func, *args, **kwds):
        return func(HydraBot.__HydraBot, *args, **kwds)

    @staticmethod
    def main(bot: HydraBot):
        return bot.run()

    def run(self):
        return HydraBot.__DP.run_polling(self)

    @staticmethod
    @__DP.message(commands={"hello"})
    async def hello(msg: types.Message):
        await msg.answer(f"Hello, <b>{msg.from_user.full_name}!</b>")

