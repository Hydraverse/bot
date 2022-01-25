from aiogram import types

from . import HydraBot
from .data import HydraBotData, schemas


async def addr(bot: HydraBot, msg: types.Message):
    address = str(msg.text).replace("/addr", "", 1).strip()

    if not address:
        return await msg.answer(
            "Add: <b>/addr [HYDRA or smart contract address]</b>\n"
            "Remove: <b>/addr [HYDRA or smart contract address] del</b>\n"
            "List: <b>/addr list</b>"
        )

    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True)

    if address == "list":
        result = []

        if len(u.user_addrs):
            result += [f"Addresses:\n"]
            result += [
                f"<pre>{str(ua.addr)}</pre>"
                for ua in u.user_addrs
            ] + ["\n"]

        if not len(result):
            result = ["No addresses yet."]

        return await msg.answer("\n".join(result))

    if address.endswith(" del"):
        address = address.replace(" del", "", 1).strip()

        for ua in u.user_addrs:
            if str(ua.addr) == address:
                delete_result: schemas.DeleteResult = await bot.db.asyncc.user_addr_del(u, ua)
                if delete_result.deleted:
                    return await msg.answer("Address removed.\n")
                break

        return await msg.answer("Address not removed: not found.\n")

    for ua in u.user_addrs:
        if str(ua.addr) == address:
            return await msg.answer(
                "Address already added.\n"
                "List: <b>/addr list</b>"
            )

    user_addr = await bot.db.asyncc.user_addr_add(u, address)
    addr_: schemas.Addr = user_addr.addr

    tp_str = (
        str(addr_.addr_tp.value.value).upper() if addr_.addr_tp.value == schemas.Addr.Type.H else
        (
                f"{addr_.info.get('qrc20', addr_.info.get('qrc721', {})).get('name', 'Unknown')} " +
                str(addr_.addr_tp.value.value)
        )
    )

    addr_str = str(addr_)

    return await msg.answer(f"Added {tp_str} address:\n<pre>{addr_str}</pre>")

