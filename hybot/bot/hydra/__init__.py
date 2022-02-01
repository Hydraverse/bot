"""Created by Halospace Foundation.
Support: @TheHydraverse
"""
from __future__ import annotations

from decimal import Decimal

import requests.exceptions
from aiogram import Bot, Dispatcher, types
import asyncio
from attrdict import AttrDict
from datetime import datetime, timedelta

from hydra.rpc.explorer import ExplorerRPC
from hydra import log

from hydb.api.client import HyDbClient, schemas
from hydra.kc.prices import PriceClient

from hybot.util.conf import Config
from num2words import num2words

from .data import HydraBotData


@Config.defaults
class HydraBot(Bot):
    _: HydraBot = None
    dp = Dispatcher()

    conf: AttrDict
    db: HyDbClient
    rpcx: ExplorerRPC
    prices: PriceClient
    coin: dict

    CONF = {
        "token": "(bot token from @BotFather)",
        "admin": -1,
        "donations": "HUo97u33iEdkEWBiLZEitAsGRXHUcmdfHQ",
        "kc_key": "(KuCoin API key)",
        "kc_sec": "(KuCoin API secret)",
        "kc_psp": "(KuCoin API passphrase)",
    }

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def bot(*self) -> HydraBot:
        return HydraBot._

    def __new__(cls, db: HyDbClient, *args, **kwds):
        if cls._ is None:
            cls._ = super(HydraBot, cls).__new__(cls, *args, **kwds)

        return cls._

    def __hash__(self):
        return hash(self.conf.token)

    def __init__(self, db: HyDbClient):
        self.db = db
        self.conf = Config.get(HydraBot, defaults=True)

        self.prices = PriceClient(
            api_key=self.conf.kc_key,
            api_secret=self.conf.kc_sec,
            passphrase=self.conf.kc_psp
        )

        self.prices._cache.expiry = timedelta(minutes=1)

        self.coin = self.prices.kuku.get_currency(self.prices.coin)

        token = self.conf.token

        if not token:
            raise ValueError("Invalid or no token found in config")

        HydraBotData.init(self.db)

        self.rpcx = ExplorerRPC(mainnet=HydraBotData.SERVER_INFO.mainnet)

        from . import \
            hello as cmd_hello,\
            tz as cmd_tz,\
            addr as cmd_addr,\
            delete as cmd_delete, \
            fiat as cmd_fiat

        @HydraBot.dp.message(commands={"hello", "start", "hi", "help"})
        async def hello(msg: types.Message):
            return await self.command(msg, cmd_hello.hello)

        @HydraBot.dp.message(commands={"tz"})
        async def tz(msg: types.Message):
            return await self.command(msg, cmd_tz.tz)

        @HydraBot.dp.message(commands={"addr", "a"})
        async def addr_(msg: types.Message):
            return await self.command(msg, cmd_addr.addr)

        @HydraBot.dp.message(commands={"DELETE"})
        async def delete(msg: types.Message):
            return await self.command(msg, cmd_delete.delete)

        @HydraBot.dp.message(commands={"fiat", "price"})
        async def delete(msg: types.Message):
            return await self.command(msg, cmd_fiat.fiat)

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(db: HyDbClient):
        return HydraBot(db).run()

    def hydra_fiat_value(self, currency: str, value, *, with_name=True):
        fiat_value = round(
            Decimal(self.prices.price(currency, raw=True))
            * schemas.Addr.decimal(value),
            2
        )

        # noinspection StrFormat
        return self.prices.format(
            currency,
            '{:,}'.format(fiat_value),
            with_name=with_name
        )

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
        users_notified = 0

        for addr_hist in block_sse_result.hist:
            for addr_hist_user in addr_hist.addr_hist_user:
                users_notified += await self.__sse_block_event_user_proc(block_sse_result, addr_hist, addr_hist_user)

        log.info(f"Block #{block_sse_result.block.height} {block_sse_result.event}: Notified {users_notified} user{'s' if users_notified != 1 else ''}.")

    async def __sse_block_event_user_proc(self, block_sse_result: schemas.BlockSSEResult, addr_hist: schemas.AddrHistResult, addr_hist_user: schemas.UserAddrHistResult):
        if block_sse_result.event == schemas.SSEBlockEvent.create:
            if addr_hist.mined:
                await self.__sse_block_event_user_mined(block_sse_result.block, addr_hist, addr_hist_user)
                return 1
        elif block_sse_result.event == schemas.SSEBlockEvent.mature:
            if addr_hist.mined:
                await self.__sse_block_event_user_mined_matured(block_sse_result.block, addr_hist, addr_hist_user)
                return 1

        log.warning(f"Unprocessed BlockSSEResult for user {addr_hist_user.user_addr.user.uniq.name}: {block_sse_result.dict()}")
        return 0

    async def __sse_block_event_user_mined(self, block: schemas.Block, addr_hist: schemas.AddrHistResult, addr_hist_user: schemas.UserAddrHistResult):
        user_addr: schemas.UserAddrResult = addr_hist_user.user_addr
        user: schemas.UserBase = user_addr.user

        staking = int(addr_hist.info_new["staking"])
        staking_delta = staking - int(addr_hist.info_old["staking"])

        staking_delta_dec = schemas.Addr.decimal(staking_delta)

        if staking_delta_dec != 0 and staking_delta != staking:
            staking_delta_dec = f" ({'+' if staking_delta_dec > 0 else ''}{str(staking_delta_dec)})"
        else:
            staking_delta_dec = " +" if staking_delta == staking else ""

        staking_tot = f"{'{:,}'.format(schemas.Addr.decimal(staking))} HYDRA{staking_delta_dec}"

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

        utxo_out_tot = schemas.Addr.decimal(utxo_out_tot, prec=5)

        utxo_str = "Merged" if utxo_inp_cnt > utxo_out_cnt else "Updated" if utxo_inp_cnt == utxo_out_cnt else "Split"
        utxo_str += f" {num2words(utxo_inp_cnt)} UTXO{'s' if utxo_inp_cnt != 1 else ''}"

        if utxo_inp_cnt != utxo_out_cnt:
            utxo_str += f" into {num2words(utxo_out_cnt)}"

        utxo_str += f" with a total output of about {utxo_out_tot} HYDRA."

        reward = block.info["reward"]
        currency = user.info.get("fiat", "USD")
        value = self.hydra_fiat_value(currency, reward)
        reward = schemas.Addr.decimal(reward, prec=4)
        price = self.hydra_fiat_value(currency, 1 * 10**8, with_name=False)

        message = [
            f'<b><a href="{self.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a> '
            + f'mined a new <a href="{self.rpcx.human_link("block", block.height)}">block</a>!</b>\n',
            f'Reward: <a href="{self.rpcx.human_link("tx", block_tx["id"])}">+{reward}</a> HYDRA',
            f"Value:  {value} @ {price}",
            f"Stake:  {staking_tot}",
            "",
            utxo_str,
        ]

        if addr_hist_user.block_t is not None:
            td: timedelta = datetime.utcnow() - addr_hist_user.block_t
            td_msg = schemas.timedelta_str(td)

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

        staking = schemas.Addr.decimal(addr_hist.info_new["staking"])

        utxo_out_tot = 0

        block_tx = block.tx[1]

        for out in filter(lambda out_: out_.get("address") == addr_hist.addr.addr_hy, block_tx["outputs"]):
            value = int(out.get("value", 0))

            if value:
                utxo_out_tot += value

        matured = (
            int(addr_hist.info_new["mature"]) -
            int(addr_hist.info_old["mature"])
        )

        matured_str = ""

        if matured != 0 and matured != utxo_out_tot:
            matured = schemas.Addr.decimal(matured)
            matured_str = f" ({'+' if matured > 0 else ''}{matured})"

        utxo_out_tot = schemas.Addr.decimal(utxo_out_tot)

        reward = schemas.Addr.decimal(block.info["reward"], prec=4)

        message = [
            f'<b>{user.uniq.name} :: <a href="{self.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a></b>',
            "",
            f'Block <a href="{self.rpcx.human_link("block", block.hash)}">#{block.height}</a> has matured!',
            f"Reward: +{reward} HYDRA",
            f"Matured: +{utxo_out_tot}{matured_str}",
        ]

        if staking > 0:
            message += [
                f"Staking: {staking} HYDRA",
            ]

        await self.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )

