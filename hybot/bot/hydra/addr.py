from sqlalchemy.exc import IntegrityError
from aiogram import types

from . import HydraBot
from ...data import User, UserAddr, Addr
from .user import HydraBotUser


async def addr(bot: HydraBot, msg: types.Message):
    try:
        address = str(msg.text).replace("/addr", "", 1).strip()

        if not address:
            return await msg.answer(
                "Add: <b>/addr [HYDRA or smart contract address]</b>\n"
                "Remove: <b>/addr [HYDRA or smart contract address] del</b>\n"
                "List: <b>/addr list</b>"
            )

        u = await HydraBotUser.load(bot.db, msg, create=True, full=True)

        if address == "list":
            if not len(u.addrs):
                return await msg.answer("No addresses yet.")

            result = []

            for addr_tp in (Addr.Type.H, Addr.Type.T, Addr.Type.S):
                user_addrs = tuple(filter(lambda adr: adr.addr_tp is addr_tp, u.addrs))

                if len(user_addrs):
                    tp_str = str(addr_tp.value).capitalize() if addr_tp is not Addr.Type.H else str(addr_tp.value)
                    adr_str = lambda adr: (
                        adr.addr_hy if addr_tp == Addr.Type.H else
                        adr.addr_hx if addr_tp == Addr.Type.S else
                        (
                            f"{adr.info.get('sc', {}).get('sym', '???')}: "
                            f"{adr.info.get('sc', {}).get('name', '(Unknown name)')}\n"
                            f"{adr.addr_hx}\n"
                        )
                    )

                    result.append(f"{tp_str} addresses:\n")
                    result += [
                        f"<pre>{adr_str(adr)}</pre>"
                        for adr in user_addrs
                    ] + ["\n"]

            return await msg.answer("\n".join(result))

        if address.endswith(" del"):
            address = address.replace(" del", "", 1).strip()

            if await User.addr_del(bot.db, u.pkid, address) is not None:
                return await msg.answer("Address removed.\n")

            return await msg.answer("Address not removed: not found.\n")

        try:
            user_addr = await User.addr_add(bot.db, u.pkid, address)
            addr_ = user_addr.addr

        except IntegrityError:
            return await msg.answer(
                "Address already added.\n"
                "List: <b>/addr list</b>"
            )

        tp_str = (
            str(addr_.addr_tp.value).upper() if addr_.addr_tp == Addr.Type.H else
            (
                f"{addr_.info.sc.get('sym', addr_.info.sc.get('name', 'unnamed'))} " +
                str(addr_.addr_tp.value)
            )
        )

        addr_str = addr_.addr_hy if addr_.addr_tp == Addr.Type.H else addr_.addr_hx

        return await msg.answer(f"Added {tp_str} address:\n<pre>{addr_str}</pre>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{str(error)}</b>")
        raise
