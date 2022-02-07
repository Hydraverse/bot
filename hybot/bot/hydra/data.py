from typing import Optional

from aiogram.types import Message

from hydra.rpc import BaseRPC
from hydb.api.client import HyDbClient, schemas

from . import HydraBot


class HydraBotData:
    __CREATING__ = []

    SERVER_INFO: schemas.ServerInfo

    PKID_CACHE = {}

    @staticmethod
    def init(db: HyDbClient):
        HydraBotData.SERVER_INFO = db.server_info()
        HydraBotData.PKID_CACHE = db.user_map().map

    @staticmethod
    async def _user_load_cached(bot: HydraBot, tg_user_id: int) -> schemas.User:
        if tg_user_id in HydraBotData.PKID_CACHE:
            return await bot.db.asyncc.user_get(user_pk=HydraBotData.PKID_CACHE[tg_user_id])

        u: schemas.User = await bot.db.asyncc.user_get_tg(tg_user_id)

        HydraBotData.PKID_CACHE[tg_user_id] = u.uniq.pkid

        return u

    @staticmethod
    async def user_load(bot: HydraBot, msg: Message, create: bool = True, requires_start: bool = True, dm_only: bool = True) -> Optional[schemas.User]:
        if msg.from_user.id in HydraBotData.__CREATING__:
            raise RuntimeError("Currently creating user account!")

        if msg.chat.id < 0 and dm_only:
            await msg.reply(f"Hi {msg.from_user.first_name}, that function is only available in a private chat.")
            return

        try:
            u: schemas.User = await HydraBotData._user_load_cached(bot, msg.from_user.id)

            if msg.chat.id < 0 and requires_start and "tz" not in u.info:
                bot_name = (await bot.get_me()).username
                await msg.reply(f"Hi {msg.from_user.first_name}!\nTo get started please send <pre>/start</pre> privately to me at @{bot_name}.")
                return

            return u

        except BaseRPC.Exception as exc:
            if exc.response.status_code == 404:
                if msg.chat.id < 0 and requires_start:
                    bot_name = (await bot.get_me()).username
                    await msg.reply(f"Hi {msg.from_user.first_name}!\nTo get started please send <pre>/start</pre> privately to me at @{bot_name}.")
                    return

                if create:
                    if msg.from_user.id in HydraBotData.__CREATING__:
                        raise RuntimeError("Currently creating user account!")

                    HydraBotData.__CREATING__.append(msg.from_user.id)

                    try:
                        await msg.answer(
                            f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n"
                            "One moment while I set things up..."
                        )

                        u: schemas.User = await HydraBotData._user_load_cached(bot, msg.from_user.id)

                        return u
                    finally:
                        HydraBotData.__CREATING__.remove(msg.from_user.id)
                else:
                    return None

            raise
