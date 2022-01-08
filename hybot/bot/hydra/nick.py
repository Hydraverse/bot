import aiogram
from aiogram import types, exceptions

from . import HydraBot
from ...data import User


async def nick(bot: HydraBot, msg: types.Message):
    u = await User.load_or_create(bot.db, msg.from_user.id)

    nick_cur = u.info.get("nick", None)
    nick_new = str(msg.text).replace("/nick", "", 1).strip()

    if not nick_new:
        return await msg.answer(
            f"Hiya, <b>{nick_cur}</b>!\n\n"
            "Change your nickname with /nick [name]"
        )

    if nick_new == nick_cur:
        return await msg.answer(f"That's your nickname already, silly {nick_cur}!")

    try:
        await User.update_info(bot.db, u.pkid, {
            "nick": nick_new,
        })
    except aiogram.exceptions.AiogramError as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{error}</b>")

    await msg.answer(f"Nickname changed to <b>{nick_new}</b>\n\n")
