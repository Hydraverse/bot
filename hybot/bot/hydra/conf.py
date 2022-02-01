from typing import Optional

from aiogram import types
from deepdiff import DeepDiff

from . import HydraBot
from .data import HydraBotData, schemas
from .addr import human_type


async def conf(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True)
    ua: Optional[schemas.UserAddr] = None

    conf_cur: dict = u.info.get("conf", {})

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
            return await msg.answer("Unable to locate that address.")

    if not conf_cmd:
        conf_block_bal = conf_cur.get('block', {}).get('bal', None)
        conf_block_bal = f"Current: {conf_block_bal}" if conf_block_bal is not None else "Default: hide"
        conf_block_stake = conf_cur.get('block', {}).get('stake', None)
        conf_block_stake = f"Current: {conf_block_stake}" if conf_block_stake is not None else "Default: hide"
        conf_block_utxo = conf_cur.get('block', {}).get('utxo', None)
        conf_block_utxo = f"Current: {conf_block_utxo}" if conf_block_utxo is not None else "Default: show"
        conf_block_mature = conf_cur.get('block', {}).get('mature', None)
        conf_block_mature = f"Current: {conf_block_mature}" if conf_block_mature is not None else "Default: full"

        return await msg.answer(
            f"Configuration management{addr_link_str}.\n\n"
            "<pre>"
            "Syntax: /conf [conf] [name] [value]\n\n"
            "Address-specific:\n"
            "/conf [addr]: [conf] [name] [value]\n\n\n"
            "Block config:\n\n"
            f"Show balance/status on new blocks:\n"
            f"/conf block bal [show|hide|full]\n"
            f"{conf_block_bal}\n\n"
            f"Show staking info on new blocks:\n"
            f"/conf block stake [show|hide|full]\n"
            f"{conf_block_stake}\n\n"
            f"Show UTXO split info on new blocks:\n"
            f"/conf block utxo [show|hide|full]\n"
            f"{conf_block_utxo}\n\n"
            f"Notify on block mature:\n"
            f"/conf block mature [show|hide|full]\n"
            f"{conf_block_mature}\n\n"
            "\n"
            "</pre>"
        )

    cmds = conf_cmd.lower().split()

    if len(cmds) != 3 or cmds[0] != "block" or cmds[1] not in ("bal", "stake", "mature", "utxo") or cmds[2] not in ("show", "hide", "full"):
        return await msg.answer("Invalid command or config value.")

    conf_cur.setdefault(cmds[0], {})[cmds[1]] = cmds[2]
    
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
