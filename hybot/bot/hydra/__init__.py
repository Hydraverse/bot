"""Created by Halospace Foundation.
Support: @TheHydraverse
"""
from __future__ import annotations

from aiogram import Bot, Dispatcher, types
import asyncio
from attrdict import AttrDict

from hydra import log

from hydb.api.client import HyDbClient, schemas

from hybot.util.conf import Config


@Config.defaults
class HydraBot(Bot):
    _: HydraBot = None
    dp = Dispatcher()

    conf: AttrDict = None
    db: HyDbClient = None

    CONF = {
        "token": "(bot token from @BotFather)",
        "admin": -1,
        "donations": "HUo97u33iEdkEWBiLZEitAsGRXHUcmdfHQ",
    }

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def bot(*self) -> HydraBot:
        return HydraBot._

    def __new__(cls, db: HyDbClient, *args, **kwds):
        if cls._ is None:
            cls._ = super(HydraBot, cls).__new__(cls, *args, **kwds)

        return cls._

    def __init__(self, db: HyDbClient):
        self.db = db
        self.conf = Config.get(HydraBot, defaults=True)

        token = self.conf.token

        if not token:
            raise ValueError("Invalid or no token found in config")

        from . import \
            hello as cmd_hello,\
            tz as cmd_tz,\
            addr as cmd_addr,\
            delete as cmd_delete

        @HydraBot.dp.message(commands={"hello", "start", "hi", "help"})
        async def hello(msg: types.Message):
            return await self.command(msg, cmd_hello.hello)

        @HydraBot.dp.message(commands={"tz", "timezone"})
        async def tz(msg: types.Message):
            return await self.command(msg, cmd_tz.tz)

        @HydraBot.dp.message(commands={"addr", "a"})
        async def addr_(msg: types.Message):
            return await self.command(msg, cmd_addr.addr)

        @HydraBot.dp.message(commands={"DELETE"})
        async def delete(msg: types.Message):
            return await self.command(msg, cmd_delete.delete)

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(db: HyDbClient):
        return HydraBot(db).run()

    @staticmethod
    @dp.message(commands={"echo"})
    async def echo(msg: types.Message):
        return await msg.answer(msg.text)

    @staticmethod
    @dp.startup()
    async def __on_startup():
        bot = HydraBot.bot()
        # TODO: Set up SSE for AddrHist events.
        # asyncio.create_task(...)

    def run(self):
        return self.dp.run_polling(self)

    async def command(self, msg, fn, *args, **kwds):
        # noinspection PyBroadException
        try:
            return await fn(self, msg, *args, **kwds)
        except BaseException as error:
            await msg.answer(
                f"Sorry, something went wrong. <b><pre>{str(error)}</pre></b>"
            )

            if log.level() <= log.INFO:
                raise
