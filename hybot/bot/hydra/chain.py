import asyncio
from decimal import Decimal

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
    hydra_val = lambda v: round(schemas.Addr.decimal(v), 2)

    current = AttrDict(stats.current.dict())

    current.apr = round(Decimal(current.apr), 2)
    current.time = current.time.strftime("%a %H:%M")

    current.block_value = schemas.Addr.decimal(current.block_value)
    current.money_supply = round(Decimal(current.money_supply), 2)
    current.net_weight = hydra_val(current.net_weight)
    
    current.net_diff_pos = round(Decimal(current.net_diff_pos), 2)
    del current.net_hash_rate
    del current.net_diff_pow

    Hybot.app().render(
        result=current,
        name="current",
        print_fn=append
    )

    if stats.quant_stat_1d is not None:
        quant_stat_1d = AttrDict(stats.quant_stat_1d.dict())

        quant_stat_1d.apr = round(Decimal(quant_stat_1d.apr), 2)
        quant_stat_1d.time = str(quant_stat_1d.time).rsplit(".", 1)[0]

        quant_stat_1d.block_value = schemas.Addr.decimal(quant_stat_1d.block_value)
        quant_stat_1d.money_supply = round(Decimal(quant_stat_1d.money_supply), 2)
        quant_stat_1d.net_weight = hydra_val(quant_stat_1d.net_weight)

        quant_stat_1d.net_diff_pos = round(Decimal(quant_stat_1d.net_diff_pos), 2)
        del quant_stat_1d.net_hash_rate
        del quant_stat_1d.net_diff_pow

        Hybot.app().render(
            result=quant_stat_1d,
            name="quant_stat_1d",
            print_fn=append
        )

    quant_net_weight = AttrDict(stats.quant_net_weight.dict())
    quant_net_weight_count = 0

    if quant_net_weight.median_1h is not None:
        quant_net_weight.median_1h = hydra_val(quant_net_weight.median_1h)
        quant_net_weight_count += 1
    else:
        del quant_net_weight.median_1h

    if quant_net_weight.median_1d is not None:
        quant_net_weight.median_1d = hydra_val(quant_net_weight.median_1d)
        quant_net_weight_count += 1
    else:
        del quant_net_weight.median_1d

    if quant_net_weight.median_1w is not None:
        quant_net_weight.median_1w = hydra_val(quant_net_weight.median_1w)
        quant_net_weight_count += 1
    else:
        del quant_net_weight.median_1w

    if quant_net_weight.median_1m is not None:
        quant_net_weight.median_1m = hydra_val(quant_net_weight.median_1m)
        quant_net_weight_count += 1
    else:
        del quant_net_weight.median_1m

    if quant_net_weight_count > 0:
        Hybot.app().render(
            result=quant_net_weight,
            name="quant_net_weight",
            print_fn=append
        )

    message = [
        "<b>Raw Blockchain Stats</b>",
        "<pre>",
        "\n\n".join(message),
        "</pre>",
        "<pre>{user_now.ctime()} {user_now.tzname()}</pre>",
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
