from datetime import timedelta, datetime
from decimal import Decimal
from typing import Optional, Union, Dict, List

import aiogram.exceptions
from aiogram import types
from attrdict import AttrDict
# from emoji import UNICODE_EMOJI_ENGLISH

from . import HydraBot
from .data import HydraBotData, schemas

_ADDR_SHOW_PREV: Dict[int, int] = {}


def addr_list_keyboard(user_addrs: List[schemas.UserAddrBase]):
    buttons = [
        types.KeyboardButton(
            text=ua.name,
        )
        for ua in sorted(user_addrs, key=lambda ua_: ua_.name)
    ]

    addr_list_button = types.KeyboardButton(
        text="List",
    )

    cols = 2 if len(buttons) > 1 else 1
    keyboard = []
    row = []

    if len(buttons) > cols:

        for button in buttons:
            row.append(button)

            if len(row) == cols:
                keyboard.append(row)
                row = []

    else:
        row = buttons

    if len(row) or len(keyboard):
        if len(row) < cols:
            row.append(addr_list_button)

            keyboard.append(row)
        else:
            keyboard.append(row)
            keyboard.append([addr_list_button])

    reply_markup = types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Address or name to show",
        selective=True,
    )

    return reply_markup


async def addr(bot: HydraBot, msg: types.Message):
    u: Optional[schemas.User] = await HydraBotData.user_load(bot, msg, create=False, dm_only=False)

    msg_text = str(msg.text).strip()

    if not msg_text.startswith("/addr"):
        if msg_text.startswith("/a"):
            address = msg_text.replace("/a", "", 1).strip()
        else:
            # Filter should not allow any other /xx command here
            address = msg_text

            # And not react in groups:
            if msg.chat.id < 0:
                return

        if not address:
            if u is None or msg.chat.id < 0:
                return

            if not await addr_show(bot, msg.chat.id, u, ua=None):
                address = None
            else:
                return
        else:
            pass
    else:
        address = str(msg.text).replace("/addr", "", 1).strip()

    if not address:
        return await msg.answer(
            "<b>Manage your addresses</b>\n\n"
            "You can also simply send me an address and I'll add it!\n"
            "If any message you send matches a label or address, it will be shown.\n"
            "You can also just type 'list' without any command to see your addresses.\n\n"
            "Add: <b>/addr [addr]</b>\n"
            "Info: <b>/addr [search]</b>\n"
            "List: <b>/addr list</b>\n"
            "Recent: <b>/a</b>\n"
            "Rename: <b>/addr [name]: [new]</b>\n"
            "Remove: <b>/addr [name] -</b>\n\n"
            "<b>Shortcuts - No command required:</b>\n"
            "List addresses: <b>list</b>\n"
            "Add with label: <b>[addr]: [name]</b>\n"
            "Show info for matches: <b>[search]</b>\n"
        )

    if u is None:
        if msg.chat.id < 0:
            return

        u: schemas.User = await HydraBotData.user_load(bot, msg, create=True, requires_start=True, dm_only=False)

        if u is None:
            return

    if address.lower() == "list":
        result = []

        reply_markup = None

        if len(u.user_addrs):
            result += [f"Addresses:"]
            result += [
                f"\n<a href=\"{bot.rpcx.human_link(human_type(ua.addr), str(ua.addr))}\">{ua.name}</a>"
                + f"{': ' if human_type(ua.addr) == 'contract' else ''}"
                + (ua.addr.info.get("qrc20", {}).get("name", ""))
                + "\n"
                + f"<pre>{str(ua.addr)}</pre>"
                for ua in sorted(u.user_addrs, key=lambda ua_: ua_.name)
            ] + ["\n"]

            reply_markup = addr_list_keyboard(u.user_addrs) if msg.chat.id > 0 else None

        if not len(result):
            result = ["No addresses yet."]

        return await msg.answer(
            text="\n".join(result),
            reply_markup=reply_markup
        )

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

    for ua in u.filter_likely_addr_matches(address):
        await addr_show(bot, msg.chat.id, u, ua)
        matched = True

    if not matched:
        if str(msg.text).startswith("/"):
            return await msg.answer("Address not found or not valid.")


async def addr_add(bot: HydraBot, msg: types.Message, u: schemas.User, address: str, label: str = ""):
    user_addr: schemas.UserAddr = await bot.db.asyncc.user_addr_add(u, address, label)
    addr_: schemas.Addr = user_addr.addr

    tp_str = (
        str(addr_.addr_tp.value.value).upper() if addr_.addr_tp.value == schemas.Addr.Type.H else
        (
                f"{addr_.info.get('qrc20', addr_.info.get('qrc721', {})).get('name', 'Unknown')} " +
                str(addr_.addr_tp.value.value)
        )
    )

    addr_str = str(addr_)

    u.user_addrs.append(user_addr)

    await msg.answer(
        f"Added {tp_str} address with label <a href=\"{bot.rpcx.human_link(human_type(user_addr.addr), addr_str)}\">{user_addr.name}</a>.",
        parse_mode="HTML",
        reply_markup=addr_list_keyboard(u.user_addrs)
    )

    return await addr_show(bot, msg.chat.id, u, user_addr)


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
                ua.name = name
                return await msg.answer(
                    f"Address renamed from {ua.name} to {name}.\n",
                    reply_markup=addr_list_keyboard(u.user_addrs)
                )
            else:
                return await msg.answer("Address wasn't renamed, the chosen name is already in use or the server had a problem.\n")

    if not schemas.Addr.soft_validate(address, testnet=not bot.rpcx.mainnet):
        return await msg.answer("Address not renamed: not found.\n")

    return await addr_add(bot, msg, u, address, name)


async def addr_del(bot: HydraBot, msg: types.Message, u: schemas.User, address: str):
    for ua in u.user_addrs:
        if str(ua.addr) == address or address.lower() == ua.name.lower():
            delete_result: schemas.DeleteResult = await bot.db.asyncc.user_addr_del(ua)
            if delete_result.deleted:
                u.user_addrs.remove(ua)
                return await msg.answer(
                    "Address removed.\n",
                    reply_markup=addr_list_keyboard(u.user_addrs)
                )
            break

    return await msg.answer("Address not removed: not found.\n")


async def addr_show(bot: HydraBot, chat_id: int, u: Union[schemas.User, schemas.UserBase],
                    ua: Optional[Union[schemas.UserAddrBase, schemas.UserAddrResult]],
                    addr_: Optional[schemas.Addr] = None,
                    *, render: bool = False) -> Union[str, bool]:
    if ua is None:
        if not isinstance(u, schemas.User):
            raise TypeError("Must provide User (not UserBase) when ua is None.")

        ua_pk = _ADDR_SHOW_PREV.get(u.uniq.pkid, None)

        for ua in u.user_addrs:
            if ua_pk is None or ua.pkid == ua_pk:
                break

        if ua is None:
            return False

    _ADDR_SHOW_PREV[u.uniq.pkid] = ua.pkid

    if addr_ is None:
        if isinstance(ua, schemas.UserAddrResult):
            raise TypeError("Must provide Addr when ua is UserAddrResult")

        addr_ = ua.addr

    ua_addr = str(addr_)
    info = AttrDict(addr_.info)

    sc_name = info.get("qrc20", {}).get("name", "")
    if sc_name:
        sc_name = ": " + sc_name

    message = [
        f'<a href="{bot.rpcx.human_link(human_type(addr_), ua_addr)}">{ua.name}</a>' + sc_name,
        f"<pre>{ua_addr}</pre>",
        "",
    ]

    def info_add_dec(name: str):
        value = int(info.get(name, 0))

        if value:
            if name == "unconfirmed":
                name = "unconf"

            message.append(
                f"<b>{name.capitalize()}:</b> {'{:,}'.format(round(schemas.Addr.decimal(value), 2))}"
                + " HYDRA"
            )

    info_add_dec("balance")

    balance = int(info.get("balance", 0))
    total_fiat_value = Decimal(0)
    hydra_fiat_value = Decimal(0)
    currency = u.info.get("fiat", "USD")

    if balance:
        hydra_fiat_value = await bot.hydra_fiat_value_dec(currency, balance)
        total_fiat_value += hydra_fiat_value
        fiat_value = bot.fiat_value_format(currency, hydra_fiat_value, with_name=True)
        fiat_price = await bot.hydra_fiat_value(currency, 1 * 10**8, with_name=False)

        message.append(
            f"<b>Value:</b> {fiat_value} @ <b>{fiat_price}</b>"
        )

    if message[-1] != "":
        message.append("")

    info_add_dec("staking")
    info_add_dec("unconfirmed")

    if info.get("balance", None) != info.get("mature", ...):
        info_add_dec("mature")

    if message[-1] != "":
        message.append("")

    token_balances = [AttrDict(tb) for tb in info.get("qrc20Balances", [])]

    if len(ua.token_l):
        token_balances = [tb for tb in token_balances if tb.addressHex in ua.token_l]

    token_balances = [tb for tb in token_balances if int(tb.balance) > 0]

    if len(token_balances):
        message += [
            "<b>Token balances:</b>",
        ]

        max_bal_len = 0

        for tb in token_balances:
            tb.balance = int(tb.balance)
            tb.decimals = int(tb.decimals)

            balance = tb.balance if tb.decimals == 0 else round(schemas.Addr.decimal(tb.balance, decimals=tb.decimals), 2)

            tb.fiat_value = Decimal(0)

            if tb.symbol in bot.price_client_map.keys():
                try:
                    tb.fiat_value = await bot.fiat_value_dec_of(
                        tb.symbol,
                        currency,
                        schemas.Addr.decimal(tb.balance, decimals=tb.decimals)
                    )

                    total_fiat_value += tb.fiat_value

                except Exception as e:
                    raise ValueError(f"Error retrieving price for {tb.symbol}/{currency}\n{type(e).__name__}: {e}") from e

            if int(balance) == balance:
                balance = int(balance)

            tb.balance = '{:,}'.format(balance)
            max_bal_len = max(len(tb.balance), max_bal_len)

        for tb in sorted(token_balances, key=lambda tb_: float(tb_.balance.replace(",", "")), reverse=True):
            if tb.fiat_value:
                tb.fiat_value = bot.fiat_value_format(currency, tb.fiat_value, with_name=total_fiat_value == 0)
                tb.fiat_value = f" ~ {tb.fiat_value}"

                if tb.symbol in bot.price_client_map.keys():
                    fiat_price = await bot.fiat_value_of(tb.symbol, currency, schemas.Addr.decimal(1 * 10**tb.decimals, decimals=tb.decimals), with_name=False)
                    tb.fiat_value += f" @ <b>{fiat_price}</b>"
            else:
                tb.fiat_value = ""

            message.append(
                "<pre>" +
                f"{tb.balance}".rjust(max_bal_len) +
                f"</pre>  <a href=\"{bot.rpcx.human_link('contract', tb.addressHex)}\">{tb.symbol}</a>{tb.fiat_value}"
            )

    if message[-1] != "":
        message.append("")

    nft_counts = [AttrDict(nft) for nft in info.get("qrc721Balances", [])]

    if len(ua.token_l):
        nft_counts = [nft for nft in nft_counts if nft.addressHex in ua.token_l]

    nft_counts = [nft for nft in nft_counts if int(nft.count) > 0]

    if len(nft_counts):
        message += [
            "<b>NFTs:</b>",
        ]

        for nft in nft_counts:
            nft.count = int(nft.count)

            message.append(
                f"<pre>{nft.count}</pre> <a href=\"{bot.rpcx.human_link('contract', nft.addressHex)}\">{nft.symbol}</a>"
            )

            # for hx, uri in nft.get("uris", {}).items():
            #     hx = hex(int(hx, 16))[2:].upper().zfill(2)
            #     message.append(
            #         f"<pre>{nft.symbol} #{hx}: \"{uri}\"</pre>"
            #     )

    if message[-1] != "":
        message.append("")

    if total_fiat_value != hydra_fiat_value:
        total_fiat_value = bot.fiat_value_format(currency, total_fiat_value, with_name=True)

        message.append(
            f"<b>Total fiat value:</b> {total_fiat_value}"
        )

    ranking = info.get("ranking", 0)

    if ranking:
        message.append(
            f"<b>Explorer ranking:</b> {ranking}"
        )

    if ua.block_c:
        message.append(
            f"<b>Hydraverse blocks:</b> {ua.block_c}"
        )

    blocks_mined = info.get("blocksMined", 0)

    if blocks_mined:
        message.append(
            f"<b>Total blocks minted:</b> {blocks_mined}"
        )

    if message[-1] != "":
        message.append("")

    now = datetime.utcnow() + timedelta(seconds=16)
    user_now: datetime = u.user_time(now)
    user_block_t: Optional[datetime] = None
    block_td: Optional[timedelta] = None

    if ua.block_t is not None:
        user_block_t = u.user_time(ua.block_t)
        block_td = now - ua.block_t

    balance_mature = Decimal(info.get("mature", 0))
    eta_sec = 0

    if balance_mature > 0 and addr_.addr_tp.value == schemas.Addr.Type.H:
        if message[-1] != "":
            message.append("")

        stats: schemas.Stats = await bot.db.stats_cache()

        if stats.quant_net_weight.median_1d is not None:
            net_weight = stats.quant_net_weight.median_1d
        else:
            net_weight = stats.current.net_weight

        block_sec = Decimal(32)

        eta_sec = int(round(net_weight * block_sec / balance_mature))

        td = eta_td = timedelta(seconds=eta_sec)

        if block_td is not None:
            td -= block_td

        eta_str = schemas.timedelta_str(td)

        eta_next = (
            user_now + td if user_block_t is None else
            user_block_t + eta_td
        )

        if block_td is not None:
            eta_meas_str = schemas.timedelta_str(eta_td)

            message.append(
                f"<b>Current block ETA:</b> <pre>{eta_meas_str}</pre>",
            )

        message += [
            f"<b>{'Next block arrives' if block_td is not None else 'Current block ETA'}:</b> <pre>{eta_str}</pre>",
            f"<pre>{eta_next.ctime()}</pre>{' (est.)' if user_block_t is None else ''}",
            ""
        ]

    if message[-1] != "":
        message.append("")

    if ua.block_t is not None:
        td_msg = schemas.timedelta_str(block_td)

        ratio_str = ""

        if eta_sec:
            elapsed_sec = round(block_td.total_seconds())
            ratio = round(Decimal(elapsed_sec) / Decimal(eta_sec), 2)

            if ratio >= 0.01:
                ratio_str = f" ~ <pre>{ratio}x</pre>"

        message += [
            f"<b>Time elapsed:</b> <pre>{td_msg}</pre>{ratio_str}\n<pre>{user_block_t.ctime()}</pre>"
        ]

    message.append(
        f"<pre>{user_now.ctime()} {user_now.tzname()}</pre>"
    )

    message = "\n".join(message)

    if not render:
        inline_keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(text="🔁 Refresh", callback_data=f"refresh:{u.uniq.pkid}:{ua.pkid}:{chat_id}"),
                types.InlineKeyboardButton(text="❌", callback_data=f"remove"),
            ]]
        )

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML",
            reply_markup=inline_keyboard
        )

    else:
        return message

    return True


def human_type(addr_: schemas.AddrBase) -> str:
    return "address" if addr_.addr_tp.value == schemas.Addr.Type.H else "contract"


def addr_link(bot: HydraBot, addr_: schemas.AddrBase, text: str) -> str:
    return f'<a href="{bot.rpcx.human_link(human_type(addr_), str(addr_))}">{text}</a>'


def addr_link_str(bot: HydraBot, addr_: str, text: str) -> str:
    """Guess address type based on length."""
    return f'<a href="{bot.rpcx.human_link("contract" if len(addr_) == 40 else "address", addr_)}">{text}</a>'
