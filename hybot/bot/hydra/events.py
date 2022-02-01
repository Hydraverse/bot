import asyncio
import requests
from num2words import num2words

from hydra import log
from hydb.api.schemas import *

from hybot.bot.hydra import HydraBot


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
                await self.__sse_block_event_user_mined_matured(block_sse_result.block, addr_hist, addr_hist_user)
                return 1

        log.warning(f"Unprocessed BlockSSEResult for user {addr_hist_user.user_addr.user.uniq.name}: {block_sse_result.dict()}")
        return 0

    async def __sse_block_event_user_mined(self, block: Block, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult):
        user_addr: UserAddrResult = addr_hist_user.user_addr
        user: UserBase = user_addr.user

        staking = int(addr_hist.info_new["staking"])
        staking_delta = staking - int(addr_hist.info_old["staking"])

        staking_delta_dec = Addr.decimal(staking_delta)

        if staking_delta_dec != 0 and staking_delta != staking:
            staking_delta_dec = f" ({'+' if staking_delta_dec > 0 else ''}{str(staking_delta_dec)})"
        else:
            staking_delta_dec = " +" if staking_delta == staking else ""

        staking_tot = f"{'{:,}'.format(Addr.decimal(staking))} HYDRA{staking_delta_dec}"

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

        utxo_out_tot = Addr.decimal(utxo_out_tot, prec=5)

        utxo_str = "Merged" if utxo_inp_cnt > utxo_out_cnt else "Updated" if utxo_inp_cnt == utxo_out_cnt else "Split"
        utxo_str += f" {num2words(utxo_inp_cnt)} UTXO{'s' if utxo_inp_cnt != 1 else ''}"

        if utxo_inp_cnt != utxo_out_cnt:
            utxo_str += f" into {num2words(utxo_out_cnt)}"

        utxo_str += f" with a total output of about {utxo_out_tot} HYDRA."

        reward = block.info["reward"]
        currency = user.info.get("fiat", "USD")
        value = self.bot.hydra_fiat_value(currency, reward)
        reward = Addr.decimal(reward, prec=4)
        price = self.bot.hydra_fiat_value(currency, 1 * 10**8, with_name=False)

        message = [
            f'<b><a href="{self.bot.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a> '
            + f'mined a new <a href="{self.bot.rpcx.human_link("block", block.height)}">block</a>!</b>\n',
            f'Reward: <a href="{self.bot.rpcx.human_link("tx", block_tx["id"])}">+{reward}</a> HYDRA',
            f"Value:  {value} @ {price}",
            f"Stake:  {staking_tot}",
            "",
            utxo_str,
            ]

        if addr_hist_user.block_t is not None:
            td: timedelta = datetime.utcnow() - addr_hist_user.block_t
            td_msg = timedelta_str(td)

            message += [
                "",
                f"Last block created {td_msg} ago."
            ]

        # if user.block_c != user_addr.block_c:
        #     message.append(
        #         f"Hydraverse blocks mined by {user.uniq.name}: {user.block_c}"
        #     )

        await self.bot.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )

    async def __sse_block_event_user_mined_matured(self, block: Block, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult):
        user_addr: UserAddrResult = addr_hist_user.user_addr
        user: UserBase = user_addr.user

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

        reward = Addr.decimal(block.info["reward"], prec=4)

        message = [
            f'<b>{user.uniq.name} :: <a href="{self.bot.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a></b>',
            "",
            f'Block <a href="{self.bot.rpcx.human_link("block", block.hash)}">#{block.height}</a> has matured!',
            f"Reward: +{reward} HYDRA",
            f"Matured: +{utxo_out_tot}{matured_str}",
        ]

        if staking > 0:
            message += [
                f"Staking: {staking} HYDRA",
            ]

        await self.bot.send_message(
            chat_id=user.tg_user_id,
            text="\n".join(message),
            parse_mode="HTML"
        )
