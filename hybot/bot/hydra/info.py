import asyncio
import datetime
from decimal import Decimal

import aiogram.exceptions
import pytz
from aiogram import types
from attrdict import AttrDict
from hydb.api import schemas

from . import HydraBot
from hybot.app import HydraBotApp


async def info(bot: HydraBot, msg: types.Message, refresh: bool = False):
    reply_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="🔁 Refresh", callback_data=f"info:refresh"),
            types.InlineKeyboardButton(text="❌", callback_data=f"remove"),
        ]]
    )

    refresh_reply_markup = None

    if refresh:
        refresh_reply_markup = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(text="♻", callback_data="-")
            ]]
        )

        await msg.edit_reply_markup(reply_markup=refresh_reply_markup)

    chain_info: schemas.ChainInfo = await bot.db.info_cache()

    results = chain_info.dict()

    message = []

    append = lambda r: message.append("\n".join(li.strip() for li in r.splitlines(keepends=True)))

    HydraBotApp.app().render(
        result=results,
        name="current",
        print_fn=append
    )

    message = [
        "<b>Blockchain Info</b>",
        "<pre>",
        "\n\n".join(message),
        "</pre>",
    ]

    message = "\n".join(message)

    if refresh:
        try:
            await msg.edit_text(
                text=message,
                reply_markup=refresh_reply_markup
            )
        except aiogram.exceptions.AiogramError:
            pass

        await asyncio.sleep(5)

        return await msg.edit_reply_markup(
            reply_markup=reply_markup
        )

    return await msg.answer(
        text=message,
        reply_markup=reply_markup
    )


def utc_time():
    tz_utc = pytz.timezone("UTC")
    return pytz.utc.localize(datetime.datetime.utcnow(), is_dst=None).astimezone(tz_utc)
