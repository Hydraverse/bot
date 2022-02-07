import json

from aiogram import types
from hydb.api import schemas

from . import HydraBot


async def chain(bot: HydraBot, msg: types.Message):
    stats: schemas.Stats = await bot.db.stats_cache()

    message = [
        "<pre>",
        json.dumps(stats.dict(), indent=2, default=str),
        "</pre>",
    ]

    return await msg.answer("\n".join(message))

