from typing import Optional

from aiogram.types import Message
from attrdict import AttrDict

from hybot.data import DB, User


class HydraBotUser:

    @staticmethod
    async def pkid(db: DB, user_id: int) -> Optional[int]:
        return await User.get_pkid(db, user_id)

    @staticmethod
    async def load(db: DB, msg: Message, full: bool = False) -> AttrDict:
        pkid = await HydraBotUser.pkid(db, msg.from_user.id)

        if pkid is None:
            await msg.answer(
                f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n"
                "One moment while I dream up a new name for your account..."
            )

        return await User.load_or_create(db, msg.from_user.id, full)
