from typing import Optional

from aiogram.types import Message
from attrdict import AttrDict

from hybot.data import DB, User


class HydraBotUser:

    @staticmethod
    async def pkid(db: DB, user_id: int) -> Optional[int]:
        return await User.get_pkid(db, user_id)

    @staticmethod
    async def load(db: DB, msg: Message, create: bool = True, full: bool = False) -> Optional[AttrDict]:
        pkid = await HydraBotUser.pkid(db, msg.from_user.id)

        if pkid is None and create:
            await msg.answer(
                f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n"
                "One moment while I set things up..."
            )

        return await User.load(db, msg.from_user.id, create=create, full=full)
