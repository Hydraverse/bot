import asyncio

import aiogram.exceptions
from aiogram import types
from attrdict import AttrDict
from hydb.api import schemas

from . import HydraBot
from hybot.hybot import Hybot


async def chain(bot: HydraBot, msg: types.Message, refresh: bool = False):
    reply_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="🔁 Refresh", callback_data=f"chain:refresh"),
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

    stats: schemas.Stats = await bot.db.stats_cache()

    message = []

    append = lambda r: message.append("\n".join(li.strip() for li in r.splitlines(keepends=True)))

    current = AttrDict(stats.current.dict())

    current.time = current.time.time().isoformat().rsplit(".", 1)[0]

    Hybot.app().render(
        result=current,
        name="current",
        print_fn=append
    )

    Hybot.app().render(
        result=stats.quant_stat_1d.dict(),
        name="quant_stat_1d",
        print_fn=append
    )

    Hybot.app().render(
        result=stats.quant_net_weight.dict(),
        name="quant_net_weight",
        print_fn=append
    )

    message = [
        "<b>Raw Blockchain Stats</b>",
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
        except aiogram.exceptions.TelegramBadRequest:
            pass

        await asyncio.sleep(5)

        return await msg.edit_reply_markup(
            reply_markup=reply_markup
        )

    return await msg.answer(
        text=message,
        reply_markup=reply_markup
    )
