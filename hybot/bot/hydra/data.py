from typing import Optional

from aiogram.types import Message
from attrdict import AttrDict

from hybot.data import DB, User, Addr


class HydraBotData:

    @staticmethod
    async def user_load(db: DB, msg: Message, create: bool = True, full: bool = False) -> Optional[AttrDict]:
        pkid = await User.get_pkid(db, msg.from_user.id)

        if pkid is None and create:
            await msg.answer(
                f"Welcome, <b>{msg.from_user.full_name}!</b>\n\n"
                "One moment while I set things up..."
            )

        return await User.get(db, msg.from_user.id, create=create, full=full)
