"""Created by Halospace Foundation.
Support: @TheHydraverse
"""
from __future__ import annotations

import asyncio
import threading
import time

from aiogram import Bot, Dispatcher, types
from attrdict import AttrDict
from hydra import log

from hydra.rpc import HydraRPC
from hybot.data import *
from hybot.conf import Config
from hybot.data.block import Block


@Config.defaults
class HydraBot(Bot):
    _: HydraBot = None
    dp = Dispatcher()

    rpc: HydraRPC = None
    conf: AttrDict = None
    db: DB = None

    CONF = {
        "token": "(bot token from @BotFather)",
        "admin": -1,
        "donations": "HUo97u33iEdkEWBiLZEitAsGRXHUcmdfHQ",
    }

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def bot(*self) -> HydraBot:
        return HydraBot._

    def __new__(cls, *args, **kwargs):
        if cls._ is None:
            cls._ = super(HydraBot, cls).__new__(cls, *args, **kwargs)

        return cls._

    def __init__(self, rpc: HydraRPC):
        self.rpc = rpc
        self.conf = Config.get(HydraBot, defaults=True)
        self.db = DB.default(self.rpc)

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
    def main(rpc: HydraRPC):
        return HydraBot(rpc).run()

    @staticmethod
    @dp.message(commands={"echo"})
    async def echo(msg: types.Message):
        return await msg.answer(msg.text)

    async def __poll_update_addrs(self):
        # user_addrs = await UserAddr.load_all(self.db)
        # print(f"loaded {len(user_addrs)} user_addrs")

        # user_pks = await UserAddr.update_txns(self.db)
        # print(f"User PKs updated: {user_pks}")

        await Block.update(self.db)

    async def __poll(self):
        while 1:
            # await self.__poll_update_addrs()
            await asyncio.sleep(10)

    @staticmethod
    @dp.startup()
    async def __on_startup():
        asyncio.create_task(HydraBot.bot().__poll())

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
