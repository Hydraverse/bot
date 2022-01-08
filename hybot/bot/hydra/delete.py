from aiogram import types

from . import HydraBot


# noinspection PyProtectedMember
async def delete(msg: types.Message):

    delete_cmd = f"/DELETE {msg.from_user.id}"

    if str(msg.text).strip() != delete_cmd:
        return await msg.answer(
            f"Permanently delete your account with <b>{delete_cmd}</b>"
        )

    await HydraBot._.db.user_delete(msg.from_user.id)

    await msg.answer(
        "All account and user data removed.\n\n"
        "<b>NOTE: Issuing further commands will create a new account.</b>\n"
    )
