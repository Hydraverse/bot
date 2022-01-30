"""Created by Halospace Foundation.
Support: @TheHydraverse
"""
from __future__ import annotations
from decimal import *
from typing import Union

import requests.exceptions
from aiogram import Bot, Dispatcher, types
import asyncio
from attrdict import AttrDict
from datetime import datetime, timedelta, timezone

from hydra.rpc.explorer import ExplorerRPC
from hydra import log

from hydb.api.client import HyDbClient, schemas

from hybot.util.conf import Config
from hybot.util import misc
from num2words import num2words

from .data import HydraBotData


@Config.defaults
class HydraBot(Bot):
    _: HydraBot = None
    dp = Dispatcher()

    conf: AttrDict
    db: HyDbClient
    rpcx: ExplorerRPC

    CONF = {
        "token": "(bot token from @BotFather)",
        "admin": -1,
        "donations": "HUo97u33iEdkEWBiLZEitAsGRXHUcmdfHQ",
    }

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def bot(*self) -> HydraBot:
        return HydraBot._

    def __new__(cls, db: HyDbClient, *args, **kwds):
        if cls._ is None:
            cls._ = super(HydraBot, cls).__new__(cls, *args, **kwds)

        return cls._

    def __init__(self, db: HyDbClient):
        self.db = db
        self.conf = Config.get(HydraBot, defaults=True)

        token = self.conf.token

        if not token:
            raise ValueError("Invalid or no token found in config")

        HydraBotData.init(self.db)

        self.rpcx = ExplorerRPC(mainnet=HydraBotData.SERVER_INFO.mainnet)

        from . import \
            hello as cmd_hello,\
            tz as cmd_tz,\
            addr as cmd_addr,\
            delete as cmd_delete

        @HydraBot.dp.message(commands={"hello", "start", "hi", "help"})
        async def hello(msg: types.Message):
            return await self.command(msg, cmd_hello.hello)

        @HydraBot.dp.message(commands={"tz", "timezone"})
        async def tz(msg: types.Message):
            return await self.command(msg, cmd_tz.tz)

        @HydraBot.dp.message(commands={"addr", "a"})
        async def addr_(msg: types.Message):
            return await self.command(msg, cmd_addr.addr)

        @HydraBot.dp.message(commands={"DELETE"})
        async def delete(msg: types.Message):
            return await self.command(msg, cmd_delete.delete)

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(db: HyDbClient):
        return HydraBot(db).run()

    def run(self):
        return self.dp.run_polling(self)

    async def command(self, msg, fn, *args, **kwds):
        # noinspection PyBroadException
        try:
            return await fn(self, msg, *args, **kwds)
        except BaseException as error:
            await msg.answer(
                f"Sorry, something went wrong. <b><pre>{error}</pre></b>"
            )

            if log.level() <= log.INFO:
                raise

    @staticmethod
    @dp.message(commands={"echo"})
    async def echo(msg: types.Message):
        # return await msg.answer(msg.text)

        await HydraBot.bot().send_message(
            chat_id=msg.from_user.id,
            text=msg.text,
        )

    @staticmethod
    @dp.startup()
    async def __on_startup():
        bot: HydraBot = HydraBot.bot()
        asyncio.create_task(bot._sse_block_task())

    async def _sse_block_task(self):
        while 1:
            try:
                await self.db.sse_block_async(self.__sse_block_event, asyncio.get_event_loop())
            except requests.exceptions.ConnectionError as exc:
                log.debug("SSE block event connection error", exc_info=exc)
            except requests.exceptions.ChunkedEncodingError as exc:
                log.debug("SSE block event connection interrupted", exc_info=exc)
            except (requests.exceptions.RequestException, requests.exceptions.BaseHTTPError) as exc:
                log.debug("SSE block event request error", exc_info=exc)
            except BaseException as exc:
                log.debug("SSE block event other error", exc_info=exc)

            await asyncio.sleep(15)

    # noinspection PyMethodMayBeStatic
    async def __sse_block_event(self, block_sse_result: schemas.BlockSSEResult):
        log.debug("SSE Block Event! #", block_sse_result.block.pkid, block_sse_result.event.value)

        for addr_hist in block_sse_result.hist:
            for addr_hist_user in addr_hist.addr_hist_user:
                await self.__sse_block_event_user_proc(block_sse_result, addr_hist, addr_hist_user)

    async def __sse_block_event_user_proc(self, block_sse_result: schemas.BlockSSEResult, addr_hist: schemas.AddrHistResult, addr_hist_user: schemas.UserAddrHistResult):
        if block_sse_result.event == schemas.SSEBlockEvent.create:
            if addr_hist.mined:
                await self.__sse_block_event_user_mined(block_sse_result.block, addr_hist, addr_hist_user)
        elif block_sse_result.event == schemas.SSEBlockEvent.mature:
            if addr_hist.mined:
                await self.__sse_block_event_user_mined_matured(block_sse_result.block, addr_hist, addr_hist_user)

    async def __sse_block_event_user_mined(self, block: schemas.Block, addr_hist: schemas.AddrHistResult, addr_hist_user: schemas.UserAddrHistResult):
        user_addr: schemas.UserAddrResult = addr_hist_user.user_addr
        user: schemas.UserBase = user_addr.user

        staking = int(addr_hist.info_new["staking"])
        staking_delta = staking - int(addr_hist.info_old["staking"])

        staking_delta_dec = HydraBot.__decimalize(staking_delta)

        if staking_delta_dec != 0:
            staking_delta_dec = f" ({'+' if staking_delta_dec > 0 else ''}{str(staking_delta_dec)})"
        else:
            staking_delta_dec = ""

        staking_tot = f"{HydraBot.__decimalize(staking)} HYDRA{staking_delta_dec}"

        utxo_inp_cnt = 0
        utxo_out_cnt = 0
        utxo_out_tot = 0

        block_tx = block.tx[1]

        for inp in filter(lambda inp_: inp_.get("address") == addr_hist.addr.addr_hy, block_tx["inputs"]):
            value = int(inp.get("value", 0))

            if value:
                utxo_inp_cnt += 1

        for out in filter(lambda out_: out_.get("address") == addr_hist.addr.addr_hy, block_tx["outputs"]):
            value = int(out.get("value", 0))

            if value:
                utxo_out_cnt += 1
                utxo_out_tot += value

        utxo_out_tot = HydraBot.__decimalize(utxo_out_tot, prec=5)

        utxo_str = "Merged" if utxo_inp_cnt > utxo_out_cnt else "Updated" if utxo_inp_cnt == utxo_out_cnt else "Split"
        utxo_str += f" {num2words(utxo_inp_cnt)} UTXO{'s' if utxo_inp_cnt != 1 else ''}"

        if utxo_inp_cnt != utxo_out_cnt:
            utxo_str += f" into {num2words(utxo_out_cnt)}"

        utxo_str += f" with a total output of about {utxo_out_tot} HYDRA."

        message = [
            f'<b><a href="{self.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a> '
            + f'mined a new <a href="{self.rpcx.human_link("block", block.height)}">block</a>!</b>',
            f'Reward: <a href="{self.rpcx.human_link("tx", block_tx["id"])}">+{HydraBot.__block_reward_str(block)}</a> HYDRA',
            f"Staking: {staking_tot}",
            "",
            utxo_str,
        ]

        if addr_hist_user.block_t is not None:
            td: timedelta = datetime.utcnow() - addr_hist_user.block_t
            td_msg = HydraBot.__timedelta_str(td)

            message += [
                "",
                f"Last block created {td_msg} ago."
            ]

        # if user.block_c != user_addr.block_c:
        #     message.append(
        #         f"Hydraverse blocks mined by {user.uniq.name}: {user.block_c}"
        #     )

        await self.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )

    async def __sse_block_event_user_mined_matured(self, block: schemas.Block, addr_hist: schemas.AddrHistResult, addr_hist_user: schemas.UserAddrHistResult):
        user_addr: schemas.UserAddrResult = addr_hist_user.user_addr
        user: schemas.UserBase = user_addr.user

        matured = HydraBot.__decimalize(
            int(addr_hist.info_new["mature"]) -
            int(addr_hist.info_old["mature"])
        )

        staking = HydraBot.__decimalize(addr_hist.info_new["staking"])

        utxo_out_tot = 0

        block_tx = block.tx[1]

        for out in filter(lambda out_: out_.get("address") == addr_hist.addr.addr_hy, block_tx["outputs"]):
            value = int(out.get("value", 0))

            if value:
                utxo_out_tot += value

        utxo_out_tot = HydraBot.__decimalize(utxo_out_tot)

        message = [
            f'<b>{user.uniq.name} :: <a href="{self.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a></b>',
            "",
            f'Block <a href="{self.rpcx.human_link("block", block.hash)}">#{block.height}</a> has matured!',
            f"Reward: +{HydraBot.__block_reward_str(block)} HYDRA",
            f"Matured: +{utxo_out_tot} (total change: {'+' if matured > 0 else ''}{matured})",
        ]

        if staking > 0:
            message += [
                f"Staking: {str(staking)} HYDRA",
            ]

        await self.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )

    @staticmethod
    def __timedelta_str(td: timedelta) -> str:
        td_msg = AttrDict()

        if td.days > 0:
            td_msg.days = str(td.days) + "d"

        seconds = td.seconds

        if seconds >= 3600:
            hours = seconds // 3600
            seconds -= hours * 3600
            td_msg.hours = str(hours) + "h"

        if seconds >= 60:
            minutes = seconds // 60
            seconds -= minutes * 60
            td_msg.minutes = str(minutes) + "m"

        if not len(td_msg):
            td_msg.seconds = str(seconds) + "s"

        return (
                td_msg.get('days', '') +
                td_msg.get('hours', '') +
                td_msg.get('minutes', '') +
                td_msg.get('seconds', '')
        )

    @staticmethod
    def __block_reward_str(block: schemas.Block) -> str:
        return str(HydraBot.__decimalize(block.info["reward"], prec=4))

    @staticmethod
    def __decimalize(value: Union[int, str], decimals: int = 8, prec: int = 16) -> Decimal:
        getcontext().prec = prec
        return Decimal(value) / Decimal(10**decimals)

