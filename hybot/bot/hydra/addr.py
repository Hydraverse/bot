from datetime import datetime
from aiogram import types
from fuzzywuzzy import fuzz
import pytz

from . import HydraBot


# noinspection PyProtectedMember
async def addr(msg: types.Message):
    u = await HydraBot._.db.user_load_or_create(msg.from_user.id)

    try:
        address = str(msg.text).replace("/addr", "", 1).strip()

        if not address:
            return await msg.answer(
                "Add: <b>/addr [HYDRA Address]</b>\n"
                "Remove: <b>/addr del [HYDRA Address]</b>\n"
                "List: <b>/addr list</b>"
            )

        if address == "list":
            if not len(u.addrs):
                return await msg.answer("No addresses yet.")

            result = ["Addresses:\n"]

            for user_addr in u.addrs:
                result.append(f"<pre>{user_addr.addr_id}</pre>")

            return await msg.answer("\n".join(result))

        if address.startswith("del "):
            address = address.replace("del ", "", 1).strip()

            for user_addr in u.addrs:
                if user_addr.addr_id == address:
                    await HydraBot._.db.user_addr_remove(u.user_id, user_addr.addr_id)
                    return await msg.answer("Address removed.\n")

            return await msg.answer("Address not removed: not found.\n")

        for user_addr in u.addrs:
            if user_addr.addr_id == address:
                return await msg.answer(
                    "Address already added.\n"
                    "List: <b>/addr list</b>"
                )

        await HydraBot._.db.user_addr_load(u.user_id, address)

        return await msg.answer(f"Added <pre>{address}</pre>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{error}</b>")
        raise
