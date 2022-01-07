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

    @staticmethod
    @__DP.message(commands={"hello"})
    async def hello(msg: types.Message):
        u = await HydraBot._.db.user_load_or_create(msg.from_user)

        nick = u.info.get("nick", None) or msg.from_user.username

        response_nick_change = (
            "Change your nickname with /nick [name]\n\n"
        )

        response_nick_is = (
            f"Your nickname is {nick}.\n" +
            response_nick_change
        )

        response_uid = (
            f"Your HydraBot user id is #{u.user_id}.\n\n"
        )

        response_donate = (
            "Please consider supporting the project developer.\n"
            "Thank You!!\n\n"
            f"{HydraBot._.conf.donations}")

        if getattr(u.info, "welcomed", False) is not True:
            await msg.answer(
                f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n" +
                response_uid +
                response_nick_is +
                response_donate
            )

            await HydraBot._.db.user_info_update(msg.from_user, {
                "welcomed": True,
                "lang": msg.from_user.language_code,
                "tz": "UTC",
                "nick": nick,
            })

        else:
            await msg.answer(
                f"Hiya, <b>{u.info.nick}!</b>\n\n" +
                response_uid +
                response_nick_change +
                response_donate
            )

    @staticmethod
    @__DP.message(commands={"nick"})
    async def hello(msg: types.Message):
        u = await HydraBot._.db.user_load_or_create(msg.from_user)

        nick_cur = u.info.get("nick", None)
        nick_new = str(msg.text).replace("/nick", "").strip()

        if not nick_new:
            return await msg.answer(
                f"Hiya, <b>{nick_cur}</b>!\n\n"
                "Change your nickname with /nick [name]"
            )

        if nick_new == nick_cur:
            await msg.answer(f"That's your nickname already, silly!\n\n")

        await msg.answer(f"Nickname changed to <b>{nick}</b>\n\n")
