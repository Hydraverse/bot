import asyncio

import pytz
import requests
from num2words import num2words

from hydra import log
from hydb.api.schemas import *

from hybot.bot.hydra import HydraBot
from hybot.bot.hydra.addr import addr_show


class EventManager:
    bot: HydraBot
    
    def __init__(self, bot: HydraBot):
        self.bot = bot
        
        @bot.dp.startup()
        async def startup():
            asyncio.create_task(self._sse_block_task())
        
    async def _sse_block_task(self):
        while 1:
            try:
                await self.bot.db.sse_block_async(self.__sse_block_event, asyncio.get_event_loop())
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
    async def __sse_block_event(self, block_sse_result: BlockSSEResult):
        users_notified = 0

        for addr_hist in block_sse_result.hist:
            for addr_hist_user in addr_hist.addr_hist_user:
                users_notified += await self.__sse_block_event_user_proc(block_sse_result, addr_hist, addr_hist_user)

        log.info(f"Block #{block_sse_result.block.height} {block_sse_result.event}: Notified {users_notified} user{'s' if users_notified != 1 else ''}.")

    async def __sse_block_event_user_proc(self, block_sse_result: BlockSSEResult, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult):
        if block_sse_result.event == SSEBlockEvent.create:
            if addr_hist.mined:
                await self.__sse_block_event_user_mined(block_sse_result.block, addr_hist, addr_hist_user)
                return 1
        elif block_sse_result.event == SSEBlockEvent.mature:
            if addr_hist.mined:
                return await self.__sse_block_event_user_mined_matured(block_sse_result.block, addr_hist, addr_hist_user)

        log.warning(f"Unprocessed BlockSSEResult for user {addr_hist_user.user_addr.user.uniq.name}: {block_sse_result.dict()}")
        return 0

    async def __sse_block_event_user_mined(self, block: Block, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult):
        user_addr: UserAddrResult = addr_hist_user.user_addr
        user: UserBase = user_addr.user

        conf = user.info.get("conf", {})
        ua_conf = user_addr.info.get("conf", {})

        conf_block_stake = ua_conf.get("block", {}).get("stake", conf.get("block", {}).get("stake", "hide"))
        conf_block_bal = ua_conf.get("block", {}).get("bal", conf.get("block", {}).get("bal", "hide"))
        conf_block_utxo = ua_conf.get("block", {}).get("utxo", conf.get("block", {}).get("utxo", "show"))

        balance_str = None

        if conf_block_bal == "show":
            balance = int(addr_hist.info_new.get("balance", 0))

            if balance:
                # currency = user.info.get("fiat", "USD")
                # fiat_value = self.bot.hydra_fiat_value(currency, balance, with_name=False)

                balance_str = (
                    f"Balance: {'{:,}'.format(round(Addr.decimal(balance), 2))} HYDRA"
                )

        if conf_block_stake == "full":
            staking = int(addr_hist.info_new["staking"])
            staking_delta = staking - int(addr_hist.info_old["staking"])

            staking_delta_dec = round(Addr.decimal(staking_delta), 2)

            if staking_delta_dec != 0 and staking_delta != staking:
                staking_delta_dec = f" ({'+' if staking_delta_dec > 0 else ''}{str(staking_delta_dec)})"
            else:
                staking_delta_dec = " +" if staking_delta == staking else ""

            staking_tot = f"{'{:,}'.format(round(Addr.decimal(staking), 2))}{staking_delta_dec}"

        elif conf_block_stake == "show":
            staking_tot = f"{'{:,}'.format(round(Addr.decimal(addr_hist.info_new['staking']), 2))}"
        else:
            staking_tot = None

        block_tx = block.tx[1]

        utxo_str = None

        if conf_block_utxo != "hide":
            utxo_inp_cnt = 0
            utxo_out_cnt = 0
            utxo_out_tot = 0

            for inp in filter(lambda inp_: inp_.get("address") == addr_hist.addr.addr_hy, block_tx["inputs"]):
                value = int(inp.get("value", 0))

                if value:
                    utxo_inp_cnt += 1

            for out in filter(lambda out_: out_.get("address") == addr_hist.addr.addr_hy, block_tx["outputs"]):
                value = int(out.get("value", 0))

                if value:
                    utxo_out_cnt += 1
                    utxo_out_tot += value

            utxo_out_tot = round(Addr.decimal(utxo_out_tot), 2)

            if conf_block_utxo == "full":
                utxo_str = "\n"
                utxo_str += "Merged" if utxo_inp_cnt > utxo_out_cnt else "Updated" if utxo_inp_cnt == utxo_out_cnt else "Split"
                utxo_str += f" {num2words(utxo_inp_cnt)} UTXO{'s' if utxo_inp_cnt != 1 else ''}"

                if utxo_inp_cnt != utxo_out_cnt:
                    utxo_str += f" into {num2words(utxo_out_cnt)}"

                utxo_str += f" with a total output of about {utxo_out_tot} HYDRA."
            else:  # == "show"
                utxo_str = f"UTXOs: +{utxo_out_tot} ({utxo_inp_cnt} ➔ {utxo_out_cnt})"

        reward = block.info["reward"]
        currency = user.info.get("fiat", "USD")
        value = await self.bot.hydra_fiat_value(currency, reward)
        reward = round(Addr.decimal(reward), 2)
        price = await self.bot.hydra_fiat_value(currency, 1 * 10**8, with_name=False)

        message = [
            f'<b><a href="{self.bot.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a> '
            + f'mined block <a href="{self.bot.rpcx.human_link("block", block.height)}">#{block.height}</a>!</b>\n',
        ]

        if balance_str is not None:
            message.append(balance_str)

        message += [
            f'Reward: <a href="{self.bot.rpcx.human_link("tx", block_tx["id"])}">+{reward}</a> HYDRA',
            f"Value: {value} @ {price}",
        ]

        if staking_tot is not None:
            message += [
                f"Staking: {staking_tot}",
            ]

        if utxo_str:
            message.append(utxo_str)

        block_time = user.user_time(
            datetime.utcfromtimestamp(block.info.get("timestamp", datetime.now()))
        )

        if message[-1] != "":
            message.append("")

        if addr_hist_user.block_t is not None:
            tz_time = user.user_time(addr_hist_user.block_t)

            td: timedelta = block_time - tz_time
            td_msg = timedelta_str(td)

            tz_time = tz_time.ctime()

            message += [
                f"Last block mined {td_msg} ago:\n{tz_time}"
            ]

        message.append(
            f"{block_time.ctime()} {block_time.tzname()}"
        )

        # if user.block_c != user_addr.block_c:
        #     message.append(
        #         f"Hydraverse blocks mined by {user.uniq.name}: {user.block_c}"
        #     )

        await self.bot.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )

        if conf_block_bal == "full":
            addr = Addr(
                info=addr_hist.info_new,
                **AttrDict(addr_hist.addr.dict())
            )

            await addr_show(self.bot, user.tg_user_id, user, user_addr, addr)

    async def __sse_block_event_user_mined_matured(self, block: Block, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult) -> int:
        user_addr: UserAddrResult = addr_hist_user.user_addr
        user: UserBase = user_addr.user

        conf = user.info.get("conf", {})
        ua_conf = user_addr.info.get("conf", {})

        conf_block_mature = ua_conf.get("block", {}).get("mature", conf.get("block", {}).get("mature", "show"))

        if conf_block_mature == "hide":
            return 0

        staking = Addr.decimal(addr_hist.info_new["staking"])

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
            matured = Addr.decimal(matured)
            matured_str = f" ({'+' if matured > 0 else ''}{matured})"

        utxo_out_tot = Addr.decimal(utxo_out_tot)

        reward = round(Addr.decimal(block.info["reward"]), 2)

        message = [
            f'<b>{user.uniq.name} :: <a href="{self.bot.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a></b>',
            "",
            f'Block <a href="{self.bot.rpcx.human_link("block", block.hash)}">#{block.height}</a> has matured!',
            f"Reward: +{reward} HYDRA",
            f"Matured: +{utxo_out_tot}{matured_str}",
        ]

        if staking > 0:
            message += [
                f"Staking: {staking}",
            ]

        await self.bot.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )

        if conf_block_mature == "full":
            addr = Addr(
                info=addr_hist.info_new,
                **AttrDict(addr_hist.addr.dict())
            )

            await addr_show(self.bot, user.tg_user_id, user, user_addr, addr)

        return 1
