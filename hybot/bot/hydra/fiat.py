from functools import lru_cache

import kucoin.exceptions
from aiogram import types
from attrdict import AttrDict

from . import HydraBot
from .data import HydraBotData, schemas


async def fiat(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True)

    fiat_cur = u.info.get("fiat", "USD")

    if str(msg.text).startswith("/price"):
        return await msg.answer(
            f"Current HYDRA price: {bot.hydra_fiat_value(fiat_cur, 1 * 10**8)}"
        )

    fiat_new = str(msg.text).replace("/fiat", "", 1).strip()

    if not fiat_new:
        return await msg.answer(
            f"Your fiat currency is <b>{fiat_cur}{' (default)' if 'fiat' not in u.info else ''}</b>.\n\n"
            "List available currencies: <b>/fiat list</b>\n"
            "Change your currency with <b>/fiat [3-letter currency name]</b>\n\n"
            f"Current HYDRA price: {bot.hydra_fiat_value(fiat_cur, 1 * 10**8)}"
        )

    fiat_new = fiat_new.upper()

    if fiat_new == "LIST":
        message = [
            f"All available fiat currencies:\n",
        ]

        for currency in bot.prices.currencies:
            kcc = get_currency(bot, currency)

            message.append(
                "<pre>"
                f"{currency}{': ' + kcc.fullName if kcc.fullName else ''}"
                f"{f' ({kcc.name})' if kcc.name != currency else ''}"
                + (" *" if currency == fiat_cur and "fiat" in u.info else "") +
                "</pre>"
            )

        return await msg.answer("\n".join(message))

    if "fiat" in u.info and fiat_new == fiat_cur:
        ccur = get_currency(bot, fiat_cur)

        return await msg.answer(
            f"Currency is already set to "
            + (
                f"{ccur.fullName} ({fiat_cur})"
                if ccur.fullName else
                fiat_cur
            )
        )

    if fiat_new not in bot.prices.currencies:
        return await msg.answer("Currency not found.")

    await bot.db.asyncc.user_info_put(
        u,
        {
            "fiat": fiat_new,
        }
    )

    ncur = get_currency(bot, fiat_new)

    return await msg.answer(
        f"Fiat currency changed to "
        + (
            f"{ncur.fullName} ({fiat_new})"
            if ncur.fullName else
            fiat_new
        )
    )


@lru_cache(maxsize=None)
def get_currency(bot: HydraBot, currency: str) -> AttrDict:
    try:
        kcc = AttrDict(bot.prices.kuku.get_currency(currency))
        return kcc
    except kucoin.exceptions.KucoinAPIException:
        return AttrDict(
            currency=currency,
            name=currency,
            fullName=None
        )
