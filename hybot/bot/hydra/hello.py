from __future__ import annotations
from aiogram import types

from . import __doc__
from . import HydraBot


# noinspection PyProtectedMember
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
