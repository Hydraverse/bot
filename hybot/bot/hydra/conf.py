from typing import Optional

from aiogram import types
from deepdiff import DeepDiff

from . import HydraBot
from .data import HydraBotData, schemas
from .addr import human_type


async def conf(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True, requires_start=True, dm_only=False)

    if u is None:
        return

    ua: Optional[schemas.UserAddr] = None

    conf_usr = conf_cur = u.info.get("conf", {})

    conf_cmd: str = str(msg.text).replace("/conf", "", 1).strip()

    address: Optional[str] = None
    addr_link_str = ""

    if ":" in conf_cmd:
        address, conf_cmd = [" ".join(s.strip().split()) for s in conf_cmd.split(":", 1)]
            
    if address is not None:
        for ua in u.user_addrs:
            if str(ua.addr) == address or ua.name.lower() == address.lower():
                break
        else:
            ua = None
    
        if ua is not None:
            conf_cur = ua.info.get("conf", {})

            addr_link_str = f" for <a href=\"{bot.rpcx.human_link(human_type(ua.addr), str(ua.addr))}\">{ua.name}</a>"
        else:
            await msg.answer("Unable to locate that address.")
            conf_cmd = ""

    if not conf_cmd:
        conf_block = conf_cur.get("block", {})
        conf_block_usr = conf_usr.get("block", {})
        
        conf_block_bal = conf_block.get('bal', None if not ua else conf_block_usr.get('bal', None))
        conf_block_bal = f"Current{' (for user)' if ua and 'bal' not in conf_block else ''}: {conf_block_bal}" if conf_block_bal is not None else "Default: hide"
        conf_block_stake = conf_block.get('stake', None if not ua else conf_block_usr.get('stake', None))
        conf_block_stake = f"Current{' (for user)' if ua and 'stake' not in conf_block else ''}: {conf_block_stake}" if conf_block_stake is not None else "Default: hide"
        conf_block_utxo = conf_block.get('utxo', None if not ua else conf_block_usr.get('utxo', None))
        conf_block_utxo = f"Current{' (for user)' if ua and 'utxo' not in conf_block else ''}: {conf_block_utxo}" if conf_block_utxo is not None else "Default: show"
        conf_block_mature = conf_block.get('mature', None if not ua else conf_block_usr.get('mature', None))
        conf_block_mature = f"Current{' (for user)' if ua and 'mature' not in conf_block else ''}: {conf_block_mature}" if conf_block_mature is not None else "Default: full"
        conf_block_total = conf_block.get('total', None if not ua else conf_block_usr.get('total', None))
        conf_block_total = f"Current{' (for user)' if ua and 'total' not in conf_block else ''}: {conf_block_total}" if conf_block_total is not None else "Default: hide"
        conf_block_tx = conf_block.get('tx', None if not ua else conf_block_usr.get('tx', None))
        conf_block_tx = f"Current{' (for user)' if ua and 'tx' not in conf_block else ''}: {conf_block_tx}" if conf_block_tx is not None else "Default: show"
        conf_block_notify = conf_block.get('notify', None if not ua else conf_block_usr.get('notify', None))
        conf_block_notify = (
            conf_block_notify if not isinstance(conf_block_notify, int) else
            "(notifying in group only with 'here')"
            if conf_block_notify < 0 else
            "(notifying privately and in group with 'both')"
        )
        conf_block_notify = f"Current{' (for user)' if ua and 'notify' not in conf_block else ''}: {conf_block_notify}" if conf_block_notify is not None else "Default: priv"

        return await msg.answer(
            f"<b>Configuration management{addr_link_str}.</b>\n\n"
            "<pre>"
            "Syntax: /conf [conf] [name] [value]\n"
            "Delete: /conf [conf] [name] -\n\n"
            "</pre>"
            "Address-specific:\n"
            "<b>/conf [addr]: [conf] [name] [value]</b>\n\n"
            "<pre>Block config:</pre>\n\n"
            f"Notifications for new blocks:\n"
            f"<b>/conf block notify [here|priv|both|hide]</b>\n"
            f"{conf_block_notify}\n\n"
            f"Notifications for new transactions:\n"
            f"<b>/conf block tx [show|hide|full]</b>\n"
            f"{conf_block_tx}\n\n"
            f"Notify on block mature:\n"
            f"<b>/conf block mature [show|hide|full]</b>\n"
            f"{conf_block_mature}\n\n"
            f"Show balance/status on new blocks:\n"
            f"<b>/conf block bal [show|hide|full]</b>\n"
            f"{conf_block_bal}\n\n"
            f"Show staking info on new blocks:\n"
            f"<b>/conf block stake [show|hide|full]</b>\n"
            f"{conf_block_stake}\n\n"
            f"Show UTXO split info on new blocks:\n"
            f"<b>/conf block utxo [show|hide|full]</b>\n"
            f"{conf_block_utxo}\n\n"
            f"Show total mined on new block:\n"
            f"<b>/conf block total [show|hide|full]</b>\n"
            f"{conf_block_total}\n\n"
            "\n"
        )

    cmds = conf_cmd.lower().split()

    if len(cmds) != 3 or cmds[0] != "block" or \
            cmds[1] not in ("bal", "stake", "mature", "utxo", "total", "notify", "tx") or \
            (cmds[1] != "notify" and cmds[2] not in ("show", "hide", "full", "-")) or \
            (cmds[1] == "notify" and cmds[2] not in ("here", "priv", "both", "hide", "-")):
        return await msg.answer("Invalid command or config value.")

    if cmds[1] == "notify" and cmds[2] in ("here", "both"):
        if msg.chat.id == msg.from_user.id:
            return await msg.answer("This config must be set from a group chat.")

        if msg.from_user.id not in [admin.user.id for admin in await bot.get_chat_administrators(msg.chat.id)]:
            return await msg.answer("Only group admins can set this config.")

        if cmds[2] == "both":
            # noinspection PyTypeChecker
            cmds[2] = -msg.chat.id
        else:
            # noinspection PyTypeChecker
            cmds[2] = msg.chat.id

    if cmds[2] != "-":
        conf_cur.setdefault(cmds[0], {})[cmds[1]] = cmds[2]
    else:
        if cmds[0] in conf_cur and cmds[1] in conf_cur[cmds[0]]:
            del conf_cur[cmds[0]][cmds[1]]
        else:
            conf_cur.clear()

    if len(conf_cur):

        if ua is not None:
            if "conf" not in ua.info or DeepDiff(dict(ua.info.conf), conf_cur):
                ua.info.conf = conf_cur
                
                ur: schemas.UserAddrUpdate.Result = await bot.db.asyncc.user_addr_upd(
                    ua, schemas.UserAddrUpdate(
                        info=ua.info,
                        over=True
                    )
                )
                
                if not ur.updated:
                    return await msg.answer("Unable to update config, please try again.")
            else:
                return await msg.answer("Config unchanged.")

        elif "conf" not in u.info or DeepDiff(dict(u.info.conf), conf_cur):
            u.info.conf = conf_cur
            
            await bot.db.asyncc.user_info_put(user=u, info=u.info, over=True)
            
        else:
            return await msg.answer("Config unchanged.")

        return await msg.answer(f"Config updated{addr_link_str}.")

    return await msg.answer("Config unchanged.")
