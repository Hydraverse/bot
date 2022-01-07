from __future__ import annotations
from aiogram import Bot, Dispatcher, types
from aiogram.types.user import User as TelegramUser
from attrdict import AttrDict
import asyncio

from hydra.rpc import HydraRPC

from ..data import *
from ..conf import Config

CONF = {
    "token": "(bot token from @BotFather)",
    "donations": "(developer address to shill for donations)"
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
        self.db = DB.default()

        token = self.conf.get("token", None)

        if not token:
            raise ValueError("Invalid or no token found in config")

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(bot: HydraBot):
        return bot.run()

    def run(self):
        return HydraBot.__DP.run_polling(self)

    def db_get_user(self, tg_user: TelegramUser):
        return self.db.user_load_or_create(tg_user)

    async def db_get_user_async(self, tg_user: TelegramUser):
        return await asyncio.get_event_loop().run_in_executor(None, self.db_get_user, tg_user)

    @staticmethod
    @__DP.message(commands={"hello"})
    async def hello(msg: types.Message):
        user_data = await HydraBot._.db_get_user_async(msg.from_user)

        await msg.answer(f"Hello, <b>{msg.from_user.full_name}!</b> Your HydraBot user id is #{user_data.user_id}")


