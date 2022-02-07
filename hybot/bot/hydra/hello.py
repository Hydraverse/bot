from __future__ import annotations
from aiogram import types

# noinspection PyUnresolvedReferences
from num2words import num2words

from . import __doc__
from . import HydraBot

from .data import HydraBotData, schemas


async def hello(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot, msg, create=True, requires_start=False, dm_only=True)

    if u is None:
        return

    response_intro = (
        "<pre>Welcome to the Hydraverse.</pre>\n\n"
        "I'm the $HYDRA staking and transaction notification bot, and "
        "I wish you all the best luck on your staking journey.\n\n"
        f"Your AI-generated user name is\n<pre>{u.uniq.name}.</pre>\n\n"
        f"You are the {num2words(u.uniq.pkid, ordinal=True)} staker to join.\n"
    )

    total_blocks = sum(ua.block_c for ua in u.user_addrs)

    if total_blocks:
        response_intro += (
            f"Total blocks mined: {total_blocks}\n"
        )

    response_intro += "\n"

    response_cmds = (
        "You can get started by simply sending me a message with your favorite HYDRA address.\n\n"
        "I'll keep an eye on it and let you know if anything exciting happens!\n\n"
        "<b>I can also understand some commands:</b>\n\n"
        "Manage addresses: <b>/addr</b>\n"
        "Show last address: <b>/a</b>\n\n"
        "Configuration: <b>/conf</b>\n\n"
        "Check HYDRA price: <b>/price</b>\n\n"
        f"Your fiat currency is <b>{u.info.get('fiat', 'USD (default)')}</b>.\n"
        "List currencies: <b>/fiat list</b>\n"
        "Change currency: <b>/fiat [name]</b>\n\n"
        f"Your time zone is <b>{u.info.get('tz', 'UTC')}</b>.\n"
        "Change your time zone: <b>/tz [zone]</b>\n"
        "Find a timezone: <b>/tz find [search]</b>\n\n"
        "Delete your data: <b>/DELETE</b>\n\n"
    )

    # noinspection PyGlobalUndefined
    global __doc__

    if HydraBot.CONF.donations not in bot.conf.donations:
        __doc__ += f"<b><pre>{HydraBot.CONF.donations}</pre></b>\n"

    response_donate = (
            "Please consider supporting this and future projects.\n\n"
            "<b>Thank You!!</b>\n\n"
            f"<pre>{bot.conf.donations}</pre>\n" + __doc__)

    await msg.answer(
        response_intro +
        response_cmds +
        response_donate
    )

    if u.info.get("tz", ...) is ...:

        await bot.db.asyncc.user_info_put(
            u,
            {
                "lang": msg.from_user.language_code,
                "tz": "UTC",
            }
        )
