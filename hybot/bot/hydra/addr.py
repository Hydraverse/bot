from sqlalchemy.exc import IntegrityError
from aiogram import types

from . import HydraBot
from .data import HydraBotData, User, Addr


async def addr(bot: HydraBot, msg: types.Message):
    try:
        address = str(msg.text).replace("/addr", "", 1).strip()

        if not address:
            return await msg.answer(
                "Add: <b>/addr [HYDRA or smart contract address]</b>\n"
                "Remove: <b>/addr [HYDRA or smart contract address] del</b>\n"
                "List: <b>/addr list</b>"
            )

        u = await HydraBotData.user_load(bot.db, msg, create=True, full=True)

        if address == "list":
            result = []

            if len(u.user_addrs):
                result += [f"{Addr.Type.H.value} addresses:\n"]
                result += [
                    f"<pre>{ua.addr.addr_hy}</pre>"
                    for ua in u.user_addrs
                ] + ["\n"]

            if len(u.user_tokns):
                result += [f"{Addr.Type.T.value.capitalize()} addresses:\n"]
                result += [
                    f"<pre>{ut.tokn.symb}: {ut.tokn.name}\n{ut.tokn.addr_hx}</pre>"
                    for ut in u.user_tokns
                ] + ["\n"]

            if not len(result):
                result = ["No addresses yet."]

            return await msg.answer("\n".join(result))

        if address.endswith(" del"):
            address = address.replace(" del", "", 1).strip()

            if await User.addr_del(bot.db, u.pkid, address) is not None:
                return await msg.answer("Address removed.\n")

            return await msg.answer("Address not removed: not found.\n")

        try:
            user_addr = await User.addr_add(bot.db, u.pkid, address)
            addr_ = getattr(user_addr, "addr", getattr(user_addr, "tokn", None))

        except IntegrityError:
            return await msg.answer(
                "Address already added.\n"
                "List: <b>/addr list</b>"
            )

        tp_str = (
            str(addr_.addr_tp.value).upper() if addr_.addr_tp == Addr.Type.H else
            (
                    f"{getattr(addr_, 'symb', None) or addr_.name} " +
                    str(addr_.addr_tp.value)
            )
        )

        addr_str = addr_.addr_hy if addr_.addr_tp == Addr.Type.H else addr_.addr_hx

        return await msg.answer(f"Added {tp_str} address:\n<pre>{addr_str}</pre>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{str(error)}</b>")
        raise
