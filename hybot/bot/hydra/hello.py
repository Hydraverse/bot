from __future__ import annotations
from aiogram import types

from . import __doc__
from . import HydraBot

from ...data import User


async def hello(bot: HydraBot, msg: types.Message):
    u = await User.load_or_create(bot.db, msg.from_user.id)

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
        f"Your HydraBot user id is #{u.pkid}.\n\n"
    )

    global __doc__

    if HydraBot.CONF.donations not in bot.conf.donations:
        __doc__ += f"<pre>{HydraBot.CONF.donations}</pre>\n"

    response_donate = (
            "Please consider supporting the developer of this project.\n"
            "Thank You!!\n\n"
            f"<pre>{bot.conf.donations}</pre>\n" + __doc__)

    if getattr(u.info, "welcomed", False) is not True:
        await msg.answer(
            f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n" +
            response_nick_is +
            response_uid +
            response_tz +
            response_donate
        )

        await User.update_info(bot.db, u.pkid, {
            "welcomed": True,
            "lang": msg.from_user.language_code,
            "tz": "UTC",
            "nick": nick,
        })

    else:
        await msg.answer(
            f"Hiya, <b>{u.info.nick}!</b>\n\n" +
            response_nick_change +
            response_uid +
            response_tz +
            response_donate
        )
