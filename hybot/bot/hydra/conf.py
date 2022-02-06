from __future__ import annotations
from typing import Optional, Union, Tuple, Dict, Callable, Any

from aiogram import types
from attrdict import AttrDict

from . import HydraBot
from .data import HydraBotData, schemas
from .addr import human_type

CONF_STD = "show", "hide", "full"

CONF_SECTIONS = AttrDict(
    block=dict(
        notify=dict(
            conf=("here", "priv", "both", "hide"),
            default="priv",
            label="Notifications for new blocks",
            show=lambda v: v if not isinstance(v, int) else "(notifying in group only with 'here')" if v < 0 else "(notifying in dm and group with 'both')",
            type=lambda v: int(v) if v.isnumeric() else v
        ),
        tx=dict(conf=CONF_STD, default="show", label="Notifications for new transactions"),
        bal=dict(conf=CONF_STD, default="hide", label="Show balance/addr info on new blocks"),
        utxo=dict(conf=CONF_STD, default="show", label="Show UTXO split info on new blocks"),
        stake=dict(conf=CONF_STD, default="hide", label="Show staking info on new blocks"),
        mature=dict(conf=CONF_STD, default="hide", label="Notify on block mature"),
        total=dict(conf=CONF_STD, default="hide", label="Show total mined on new block"),
    )
)

CONF = lambda i: i.setdefault("conf", {})


async def conf(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot, msg, create=True, requires_start=True, dm_only=False)

    if u is None:
        return

    ua: Optional[schemas.UserAddr] = None

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
            addr_link_str = f" for <a href=\"{bot.rpcx.human_link(human_type(ua.addr), str(ua.addr))}\">{ua.name}</a>"
        else:
            await msg.answer("Unable to locate that address.")
            conf_cmd = ""

    if not conf_cmd:
        configs: Dict[str, Dict[str, Config]] = {
            section: {
                name: Config.get(u, ua, section, name)
                for name in CONF_SECTIONS[section].keys()
            }
            for section in CONF_SECTIONS.keys()
        }

        message = [
            f"<b>Configuration management{addr_link_str}.</b>\n\n"
            "<pre>"
            "Syntax: /conf [conf] [name] [value]\n"
            "Delete: /conf [conf] [name] -\n\n"
            "</pre>"
            "Address-specific:\n"
            "<b>/conf [addr]: [conf] [name] [value]</b>"
        ]

        for section, names in configs.items():
            if message[-1] != "":
                message.append("")

            message += [
                f"<pre>{section.capitalize()} config:</pre>",
                ""
            ]

            for name, config in names.items():
                if message[-1] != "":
                    message.append("")

                value_lbl_str = "Default" if config.value is None else "Current"
                value_lbl_str += " (global)" if not config.is_ua and ua is not None else " (for addr)" if config.is_ua else ""
                value_str = config.show(config.value) if config.value is not None else config.show(config.default)

                message += [
                    f"{config.label}:",
                    f"<b>/conf {section} {name} [{'|'.join(config.conf)}]</b>",
                    f"{value_lbl_str}: {value_str}",
                    ""
                ]

        return await msg.answer(
            text="\n".join(message),
            parse_mode="HTML"
        )

    cmds = conf_cmd.lower().split()

    if len(cmds) != 3 or \
            cmds[0] not in CONF_SECTIONS or \
            cmds[1] not in CONF_SECTIONS[cmds[0]] or \
            cmds[2] not in (CONF_SECTIONS[cmds[0]][cmds[1]]["conf"] + ("-",)):
        return await msg.answer("Invalid command or config value.")

    section = cmds[0]
    name = cmds[1]
    value = cmds[2]

    if name == "notify" and value in ("here", "both"):
        if msg.chat.id == msg.from_user.id:
            return await msg.answer("This config must be set from a group chat.")

        if msg.from_user.id not in [admin.user.id for admin in await bot.get_chat_administrators(msg.chat.id)]:
            return await msg.answer("Only group admins can set this config.")

        if value == "both":
            # noinspection PyTypeChecker
            value = -msg.chat.id
        else:
            # noinspection PyTypeChecker
            value = msg.chat.id

    config = Config.get(u, ua, section, name)
    value_prev = config.value

    result = await config.set(bot, value)

    if result is None or not result.updated:
        return await msg.answer("Config unchanged.")

    return await msg.answer(
        f"Config updated{addr_link_str}:\n\n"
        f"<pre>{section}.{name}: {config.show(value_prev)} -> {config.show(config.value)}</pre>"
    )


class Config(schemas.BaseModel):
    user: schemas.UserBase
    user_addr: Optional[schemas.UserAddrBase]
    section: str
    name: str
    label: str
    conf: Tuple[str, ...]
    default: str
    value: Optional[Any]
    is_ua: bool
    show: Callable[[Any], str]

    @property
    def value_or_default(self) -> Any:
        return self.value if self.value is not None else self.default

    @staticmethod
    def info(section: str, name: str) -> AttrDict:
        if section not in CONF_SECTIONS or name not in CONF_SECTIONS[section]:
            raise ValueError(f"Invalid conf '{section}.{name}'")

        return getattr(getattr(CONF_SECTIONS, section), name)

    @staticmethod
    def get(u: schemas.UserBase, ua: Optional[schemas.UserAddrBase], section: str, name: str) -> Config:
        uic = CONF(u.info)
        uaic = CONF(ua.info) if ua is not None else None

        conf_info = Config.info(section, name)

        is_ua = False
        db_conf = uic

        if uaic is not None and section in uaic and name in uaic[section]:
            is_ua = True
            db_conf = uaic

        if section in db_conf and name in db_conf[section]:
            value = db_conf[section][name]
        else:
            if is_ua and section in uic and name in uic[section]:
                is_ua = False
                value = uic[section][name]
            else:
                value = None

        return Config(
            user=u,
            user_addr=ua,
            section=section,
            name=name,
            label=conf_info.label,
            conf=conf_info.conf,
            default=conf_info.default,
            value=value,
            is_ua=is_ua,
            show=conf_info.get("show", str)
        )

    async def set(self, bot: HydraBot, value: Optional[Any]) -> Optional[schemas.UpdateResult]:
        if value != "-" and value is not None:
            if self.value == value:
                return None

            self.value = value
            deleted = False
        else:
            self.value = None

            deleted = await self.delete()

            if not deleted:
                return None

        is_ua = self.user_addr is not None  # Override the reset value when loading global value.

        config = CONF(self.user_addr.info if is_ua else self.user.info)

        if self.value is not None:
            if self.section in config and self.name in config[self.section] and config[self.section] == self.value:
                return None

            config.setdefault(self.section, {})[self.name] = self.value

        if self.value is not None or deleted:

            if is_ua:
                return await bot.db.asyncc.user_addr_upd(
                    user_addr=self.user_addr,
                    addr_update=schemas.UserAddrUpdate(
                        info=self.user_addr.info,
                        over=False
                    )
                )

            else:
                return await bot.db.asyncc.user_info_put(
                    user=self.user,
                    info=self.user.info,
                    over=False,
                )

    async def delete(self) -> bool:
        info = self.user_addr.info if self.is_ua else self.user.info

        if "conf" not in info:
            return False

        config = CONF(info)

        deleted = False

        if self.section in config:

            if self.name in config[self.section]:
                deleted = True
                del config[self.section][self.name]

            if not len(config[self.section]):
                deleted = True
                del config[self.section]

        # Allow empty config, otherwise dict.update() doesn't work.
        #
        # if not len(config):
        #     deleted = True
        #     del info["conf"]

        return deleted
