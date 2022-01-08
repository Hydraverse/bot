from aiogram import types

from . import HydraBot
from ...data import User, UserAddr


async def addr(bot: HydraBot, msg: types.Message):
    u = await User.load_or_create(bot.db, msg.from_user.id, full=True)

    try:
        address = str(msg.text).replace("/addr", "", 1).strip()

        if not address:
            return await msg.answer(
                "Add: <b>/addr [HYDRA Address]</b>\n"
                "Remove: <b>/addr [HYDRA Address] del</b>\n"
                "List: <b>/addr list</b>"
            )

        if address == "list":
            if not len(u.addrs):
                return await msg.answer("No addresses yet.")

            result = ["Addresses:\n"]

            for user_addr in u.addrs:
                result.append(f"<pre>{user_addr.addr_id}</pre>")

            return await msg.answer("\n".join(result))

        if address.endswith(" del"):
            address = address.replace(" del", "", 1).strip()

            for user_addr in u.addrs:
                if user_addr.addr_id == address:
                    await UserAddr.remove(bot.db, u.pkid, user_addr.pkid)
                    return await msg.answer("Address removed.\n")

            return await msg.answer("Address not removed: not found.\n")

        for user_addr in u.addrs:
            if user_addr.addr_id == address:
                return await msg.answer(
                    "Address already added.\n"
                    "List: <b>/addr list</b>"
                )

        await UserAddr.add(bot.db, u.pkid, address)

        return await msg.answer(f"Added <pre>{address}</pre>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{str(error)}</b>")
        raise
