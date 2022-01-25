from aiogram import types

from . import HydraBot
from .data import HydraBotData, schemas


async def delete(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=False)

    if u is None:
        return await msg.answer(
            "You don't currently have an account."
        )

    delete_cmd = f"/DELETE {u.tg_user_id}"

    if str(msg.text).strip() != delete_cmd:
        return await msg.answer(
            f"Permanently delete your account with <b>{delete_cmd}</b>"
        )

    await bot.db.asyncc.user_del(u)

    await msg.answer(
        "All account and user data removed.\n\n"
        "<b>NOTE: Issuing further commands will create a new account.</b>\n"
    )
