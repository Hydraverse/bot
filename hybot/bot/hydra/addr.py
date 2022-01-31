from datetime import timedelta, datetime

from aiogram import types

from . import HydraBot
from .data import HydraBotData, schemas


async def addr(bot: HydraBot, msg: types.Message):
    address = str(msg.text).replace("/addr", "", 1).strip()

    if not address:
        return await msg.answer(
            "<pre>"
            "Add:    <b>/addr [addr]</b>\n"
            "Info:   <b>/addr [search]</b>\n"
            "Rename: <b>/addr [name]: [new]</b>\n"
            "Remove: <b>/addr [name] -</b>\n"
            "List:   <b>/addr list</b>"
            "</pre>"
        )

    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True)

    if address == "list":
        result = []

        if len(u.user_addrs):
            result += [f"Addresses:"]
            result += [
                f"\n<a href=\"{bot.rpcx.human_link(_human_type(ua.addr), str(ua.addr))}\">{ua.name}</a>\n"
                + f"<pre>{str(ua.addr)}</pre>"
                for ua in u.user_addrs
            ] + ["\n"]

        if not len(result):
            result = ["No addresses yet."]

        return await msg.answer("\n".join(result))

    if address.endswith(" -"):
        address = address[:-2].strip()
        return await addr_del(bot, msg, u, address)

    if ":" in address:
        address, param = [" ".join(s.strip().split()) for s in address.split(":", 1)]

        if not schemas.UserAddrUpdate.validate_name(param):
            return await msg.answer("New name must be printable, not contain punctuation and have length >= 5.")

        return await addr_rename(bot, msg, u, address, param)

    addr_tp = schemas.Addr.soft_validate(address, testnet=not bot.rpcx.mainnet)

    if addr_tp is not None:
        if address not in [str(ua.addr) for ua in u.user_addrs]:
            return await addr_add(bot, msg, u, address)

    matched = False

    for ua in u.user_addrs:
        if str(ua.addr) == address or ua.name.lower().startswith(address.lower()) or str(ua.addr).startswith(address):
            await addr_show(bot, msg, u, ua)
            matched = True

    if not matched:
        return await msg.answer("Address not found or not valid.")


async def addr_add(bot: HydraBot, msg: types.Message, u: schemas.User, address: str):
    user_addr: schemas.UserAddr = await bot.db.asyncc.user_addr_add(u, address)
    addr_: schemas.Addr = user_addr.addr

    tp_str = (
        str(addr_.addr_tp.value.value).upper() if addr_.addr_tp.value == schemas.Addr.Type.H else
        (
                f"{addr_.info.get('qrc20', addr_.info.get('qrc721', {})).get('name', 'Unknown')} " +
                str(addr_.addr_tp.value.value)
        )
    )

    addr_str = str(addr_)

    await msg.answer(
        f"Added {tp_str} address with label <a href=\"{bot.rpcx.human_link(_human_type(user_addr.addr), addr_str)}\">{user_addr.name}</a>.",
        parse_mode="HTML"
    )

    return await addr_show(bot, msg, u, user_addr)


async def addr_rename(bot: HydraBot, msg: types.Message, u: schemas.User, address: str, name: str):
    for ua in u.user_addrs:
        if str(ua.addr) == address or address == ua.name:
            update_result: schemas.UserAddrUpdate.Result = await bot.db.asyncc.user_addr_upd(
                user_addr=ua,
                addr_update=schemas.UserAddrUpdate(
                    name=name
                )
            )

            if update_result.updated:
                return await msg.answer(f"Address renamed from {ua.name} to {name}.\n")
            else:
                return await msg.answer("Address wasn't renamed, the chosen name is already in use or the server had a problem.\n")

    return await msg.answer("Address not renamed: not found.\n")


async def addr_del(bot: HydraBot, msg: types.Message, u: schemas.User, address: str):
    for ua in u.user_addrs:
        if str(ua.addr) == address or address.lower() == ua.name.lower():
            delete_result: schemas.DeleteResult = await bot.db.asyncc.user_addr_del(ua)
            if delete_result.deleted:
                return await msg.answer("Address removed.\n")
            break

    return await msg.answer("Address not removed: not found.\n")


async def addr_show(bot: HydraBot, msg: types.Message, u: schemas.User, ua: schemas.UserAddr):
    ua_addr = str(ua.addr)

    info = ua.addr.info

    message = [
        f'<a href="{bot.rpcx.human_link(_human_type(ua.addr), str(ua_addr))}">{ua.name}</a>',
        f"<pre>{ua_addr}</pre>",
        "",
    ]

    def info_add_dec(name: str):
        value = int(info.get(name, 0))

        if value:
            tab = "\t"

            if name == "unconfirmed":
                name = "unconf"

            message.append(
                f"<pre>{name.capitalize()}:{tab if len(name) >= 7 else tab*2}{schemas.Addr.decimal(value)}"
                + (" HYDRA" if name == "balance" else "")
                + "</pre>"
            )

    info_add_dec("balance")
    info_add_dec("staking")
    info_add_dec("unconfirmed")

    if info.get("balance", None) != info.get("mature", ...):
        info_add_dec("mature")

    if message[-1] != "":
        message.append("")

    token_balances = info.get("qrc20Balances", [])

    if len(ua.token_l):
        token_balances = [tb for tb in token_balances if tb.addressHex in ua.token_l]

    token_balances = [tb for tb in token_balances if int(tb.balance) > 0]

    if len(token_balances):
        message += [
            "Token balances:",
        ]

        for tb in token_balances:
            tb.balance = int(tb.balance)
            tb.decimals = int(tb.decimals)

            balance = tb.balance if tb.decimals == 0 else schemas.Addr.decimal(tb.balance, decimals=tb.decimals)

            message.append(
                f"<pre>{balance}</pre> <a href=\"{bot.rpcx.human_link('contract', tb.addressHex)}\">{tb.symbol}</a>"
            )

    if message[-1] != "":
        message.append("")

    ranking = info.get("ranking", 0)

    if ranking:
        message.append(
            f"Explorer ranking: {ranking}"
        )

    if ua.block_c:
        message.append(
            f"Hydraverse blocks: {ua.block_c}"
        )

    blocks_mined = info.get("blocksMined", 0)

    if blocks_mined:
        message.append(
            f"Total mined blocks: {blocks_mined}"
        )

    if message[-1] != "":
        message.append("")

    if ua.block_t is not None:
        td: timedelta = datetime.utcnow() - ua.block_t
        td_msg = schemas.timedelta_str(td)

        message += [
            f"Last block created {td_msg} ago."
        ]

    await msg.answer(
        "\n".join(message),
        parse_mode="HTML",
    )


def _human_type(addr_: schemas.AddrBase) -> str:
    return "address" if addr_.addr_tp.value.value == schemas.Addr.Type.H else "contract"
