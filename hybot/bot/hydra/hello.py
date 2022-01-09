from __future__ import annotations
from aiogram import types

from . import __doc__
from . import HydraBot

from ...data import User
from .user import HydraBotUser


async def hello(bot: HydraBot, msg: types.Message):
    u = await HydraBotUser.load(bot.db, msg, full=False)

    response_tz = (
        "Manage addresses with <b>/addr</b>.\n\n"
        f"Your time zone is <b>{u.info.get('tz', 'UTC')}</b>.\n"
        "Change your time zone with <b>/tz [zone]</b>\n"
        "Find a timezone with <b>/tz find [search]</b>\n\n"
    )

    response_uid = (
        f"Your unique Hydraverse ID and name:\n  <b><pre>{u.pkid}: {u.name}</pre></b>\n\n"
    )

    global __doc__

    if HydraBot.CONF.donations not in bot.conf.donations:
        __doc__ += f"<b><pre>{HydraBot.CONF.donations}</pre></b>\n"

    response_donate = (
            "Please consider supporting further development of this and other projects.\n"
            "Thank You!!\n\n"
            f"<pre>{bot.conf.donations}</pre>\n" + __doc__)

    if getattr(u.info, "tz", False) is False:
        await msg.answer(
            response_uid +
            response_tz +
            response_donate
        )

        await User.update_info(bot.db, u.pkid, {
            "lang": msg.from_user.language_code,
            "tz": "UTC",
        })

    else:
        await msg.answer(
            f"Hello, <b>{msg.from_user.username}</b>.\n\n" +
            response_tz +
            response_donate
        )
