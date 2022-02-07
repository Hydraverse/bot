from aiogram import types

from . import HydraBot
from .data import HydraBotData, schemas


async def delete(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot, msg, create=False, requires_start=False, dm_only=True)

    if u is None:
        if msg.chat.id > 0:
            await msg.answer(
                "You don't currently have an account."
            )

        return

    delete_cmd = f"/DELETE {u.tg_user_id}"

    if str(msg.text).strip() != delete_cmd:
        return await msg.answer(
            f"Permanently delete your account with <b>{delete_cmd}</b>"
        )

    await HydraBotData.user_del(bot, u)

    await msg.answer(
        "All account and user data removed.\n\n"
        "<b>NOTE: Issuing further commands will create a new account.</b>\n"
    )
