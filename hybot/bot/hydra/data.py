import asyncio
from typing import Optional

from aiogram.types import Message

from hydra.rpc import BaseRPC
from hydb.api.client import HyDbClient, schemas


class HydraBotData:
    __CREATING__ = []

    @staticmethod
    async def user_load(db: HyDbClient, msg: Message, create: bool = True) -> Optional[schemas.User]:
        if msg.from_user.id in HydraBotData.__CREATING__:
            raise RuntimeError("Currently creating user account!")

        try:
            return await HydraBotData._run_in_executor(
                db.user_get_tg,
                msg.from_user.id
            )
        except BaseRPC.Exception as exc:
            if exc.response.status_code == 404:
                if create:
                    if msg.from_user.id in HydraBotData.__CREATING__:
                        raise RuntimeError("Currently creating user account!")

                    HydraBotData.__CREATING__.append(msg.from_user.id)

                    try:
                        await msg.answer(
                            f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n"
                            "One moment while I set things up..."
                        )

                        return await HydraBotData._run_in_executor(
                            db.user_add,
                            msg.from_user.id
                        )
                    finally:
                        HydraBotData.__CREATING__.remove(msg.from_user.id)
                else:
                    return None

            raise

    @staticmethod
    async def _run_in_executor(fn, *args):
        return await asyncio.get_event_loop().run_in_executor(None, fn, *args)
