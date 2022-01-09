from sqlalchemy.exc import IntegrityError
from aiogram import types

from . import HydraBot
from ...data import User, UserAddr, Addr


async def addr(bot: HydraBot, msg: types.Message):
    u = await User.load_or_create(bot.db, msg.from_user.id, full=True)

    try:
        address = str(msg.text).replace("/addr", "", 1).strip()

        if not address:
            return await msg.answer(
                "Add: <b>/addr [HYDRA or smart contract address]</b>\n"
                "Remove: <b>/addr [HYDRA or smart contract address] del</b>\n"
                "List: <b>/addr list</b>"
            )

        if address == "list":
            if not len(u.addrs):
                return await msg.answer("No addresses yet.")

            result = []

            for addr_tp in (Addr.Type.H, Addr.Type.T, Addr.Type.S):
                addrs = tuple(filter(lambda adr: adr.addr_tp is addr_tp, u.addrs))

                if len(addrs):
                    tp_str = str(addr_tp.value).capitalize() if addr_tp is not Addr.Type.H else str(addr_tp.value)
                    result.append(f"{tp_str} addresses:\n")
                    result += [
                        f"<pre>{adr.addr_hy if addr_tp is Addr.Type.H else adr.addr_hx}</pre>"
                        for adr in addrs
                    ] + ["\n"]

            return await msg.answer("\n".join(result))

        if address.endswith(" del"):
            address = address.replace(" del", "", 1).strip()

            addr_tp, addr_hx, addr_hy = await Addr.addr_normalize(bot.db, address)

            for user_addr in u.addrs:
                if user_addr.addr_hx == addr_hx:
                    await UserAddr.remove(bot.db, u.pkid, user_addr.pkid)
                    return await msg.answer("Address removed.\n")

            return await msg.answer("Address not removed: not found.\n")

        try:
            addr_pk, addr_tp, addr_hx, addr_hy = await UserAddr.add(bot.db, u.pkid, address)

        except IntegrityError:
            return await msg.answer(
                "Address already added.\n"
                "List: <b>/addr list</b>"
            )

        tp_str = str(addr_tp.value).upper() if addr_tp is Addr.Type.H else str(addr_tp.value)

        addr_str = addr_hy if addr_tp is Addr.Type.H else addr_hx

        return await msg.answer(f"Added {tp_str} address: <pre>{addr_str}</pre>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{str(error)}</b>")
        raise
