"""Created by Halospace Foundation.
Support: t.me/TheHydraverse
"""
from __future__ import annotations
import aiogram.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.types.user import User as TelegramUser
from attrdict import AttrDict
from datetime import datetime
from fuzzywuzzy import fuzz
import pytz

from hydra.rpc import HydraRPC

from ..data import *
from ..conf import Config

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
        self.db = DB.default()

        token = self.conf.get("token", None)

        if not token:
            raise ValueError("Invalid or no token found in config")

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(rpc: HydraRPC):
        return HydraBot(rpc).run()

    def run(self):
        return HydraBot.__DP.run_polling(self)

    @staticmethod
    @__DP.message(commands={"hello"})
    async def hello(msg: types.Message):
        u = await HydraBot._.db.user_load_or_create(msg.from_user)

        nick = u.info.get("nick", None) or msg.from_user.username

        response_nick_change = (
            "Change your nickname with <b>/nick [name]</b>\n\n"
        )

        response_nick_is = (
            f"Your nickname is <b>{nick}</b>.\n" +
            response_nick_change
        )

        response_tz = (
            f"Your time zone is <b>{u.info.get('tz', 'UTC')}</b>.\n"
            "Change your time zone with <b>/tz [zone]</b>\n"
            "Find a timezone with <b>/tz find [search]</b>\n\n"
        )

        response_uid = (
            f"Your HydraBot user id is #{u.user_id}.\n\n"
        )

        response_donate = (
            "Please consider supporting the developer of this project.\n"
            "Thank You!!\n\n"
            f"<pre>{HydraBot._.conf.donations}</pre>\n" + __doc__)

        if getattr(u.info, "welcomed", False) is not True:
            await msg.answer(
                f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n" +
                response_uid +
                response_nick_is +
                response_tz +
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
                response_tz +
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
            return await msg.answer(f"That's your nickname already, silly {nick_cur}!")

        try:
            await HydraBot._.db.user_info_update(msg.from_user, {
                "nick": nick_new,
            })
        except aiogram.exceptions.AiogramError as error:
            await msg.answer(f"Sorry, something went wrong.\n\n<b>{error}</b>")

        await msg.answer(f"Nickname changed to <b>{nick_new}</b>\n\n")

    @staticmethod
    @__DP.message(commands={"tz"})
    async def tz(msg: types.Message):
        u = await HydraBot._.db.user_load_or_create(msg.from_user)

        try:
            tz_cur = u.info.get("tz", None)
            tz_new = str(msg.text).replace("/tz", "").strip()

            if not tz_new:
                return await msg.answer(
                    f"Hiya, <b>{u.info.nick}</b>!\n\n"
                    f"Your current time zone is <b>{u.info.tz}</b>.\n\n"
                    "Change your timezone with /tz [Time Zone]\n"
                    "Find a timezone with /tz find [search]"
                )

            if tz_new.startswith("find "):
                search = tz_new.split("find ", 1)[1]

                if not search:
                    return await msg.answer(
                        "Usage: /tz find [search]"
                    )

                response = "Matching time zones:\n\n"
                found = 0

                for tz in pytz.all_timezones:
                    if fuzz.token_sort_ratio(search, tz) > 66:
                        response += f"{tz}\n"
                        found += 1

                if found == 0:
                    response = "No matching time zones found."

                return await msg.answer(response)

            if tz_new == tz_cur:
                return await msg.answer(
                    f"Timezone is already <b>{tz_cur}</b>.\n"
                    "Looks like you're right where you need to be!"
                )

            tz = pytz.timezone(tz_new)
            tz_new_loc = tz.localize(datetime.now(), is_dst=None).tzname()

            await HydraBot._.db.user_info_update(msg.from_user, {
                "tz": tz_new,
            })

            await msg.answer(f"Time zone changed to <b>{tz_new} ({tz_new_loc})</b>\n\n")

        except pytz.UnknownTimeZoneError as error:
            await msg.answer(f"Sorry, that timezone is not valid.\n\n<b>{repr(error)}</b>")

        except Exception as error:
            await msg.answer(f"Sorry, something went wrong.\n\n<b>{error}</b>")
            raise

