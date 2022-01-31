from __future__ import annotations
from aiogram import types

# noinspection PyUnresolvedReferences
from . import __doc__
from . import HydraBot

from .data import HydraBotData, schemas


async def hello(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True)

    response_cmds = (
        "Manage addresses with <b>/addr</b>.\n\n"
        f"Your time zone is <b>{u.info.get('tz', 'UTC')}</b>.\n"
        "Change your time zone with <b>/tz [zone]</b>\n"
        "Find a timezone with <b>/tz find [search]</b>\n\n"
    )

    response_uid = (
        f"Your unique Hydraverse ID and name:\n  <b><pre>{u.uniq.pkid}: {u.uniq.name}</pre></b>\n\n"
    )

    # noinspection PyGlobalUndefined
    global __doc__

    if HydraBot.CONF.donations not in bot.conf.donations:
        __doc__ += f"<b><pre>{HydraBot.CONF.donations}</pre></b>\n"

    response_donate = (
            "Please consider supporting this and future projects.\n"
            "Thank You!!\n\n"
            f"<pre>{bot.conf.donations}</pre>\n" + __doc__)

    if u.info.get("tz", ...) is ...:
        await msg.answer(
            response_uid +
            response_cmds +
            response_donate
        )

        await bot.db.asyncc.user_info_put(
            u,
            {
                "lang": msg.from_user.language_code,
                "tz": "UTC",
                "at": msg.from_user.username
            }
        )

    else:
        await msg.answer(
            f"<pre>{u.uniq.pkid}: {u.uniq.name}</pre>\n\n" +
            response_cmds +
            response_donate
        )
