import asyncio
from typing import Generator

import aiogram.exceptions
import pytz
import requests
from num2words import num2words

from hydra import log
from hydb.api.schemas import *

from hybot.bot.hydra import HydraBot
from hybot.bot.hydra.addr import addr_show, addr_link, addr_link_str
from hybot.util.misc import ordinal


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
                log.info("SSE block task: Running event processing loop.")
                await self.bot.db.sse_block_async(self.__sse_block_event, asyncio.get_event_loop())
            except requests.exceptions.ConnectionError as exc:
                log.debug("SSE block event connection error", exc_info=exc)
            except requests.exceptions.ChunkedEncodingError as exc:
                log.debug("SSE block event connection interrupted", exc_info=exc)
            except (requests.exceptions.RequestException, requests.exceptions.BaseHTTPError) as exc:
                log.debug("SSE block event request error", exc_info=exc)
            except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
                log.info("SSE block task cancelled.")
                return
            except BaseException as exc:
                log.warning("SSE block event other error", exc_info=exc)

            await asyncio.sleep(1)

    # noinspection PyMethodMayBeStatic
    async def __sse_block_event(self, block_sse_result: BlockSSEResult):
        users_notified = 0
        users_notified_tx = 0

        log.debug(f"Processing Event #{block_sse_result.id} Block #{block_sse_result.block.height}")

        for addr_hist in block_sse_result.hist:
            if addr_hist.mined:
                for addr_hist_user in addr_hist.addr_hist_user:
                    users_notified += await self.__sse_block_event_user_proc(block_sse_result, addr_hist, addr_hist_user)

            if block_sse_result.event == SSEBlockEvent.create:
                users_notified_tx += await self.__sse_block_event_proc_tx(block_sse_result.block, addr_hist)

        if users_notified or users_notified_tx:
            log.info(
                f"Block #{block_sse_result.block.height} {block_sse_result.event}: Sent {users_notified} block event{'s' if users_notified != 1 else ''} "
                f"and {users_notified_tx} TX event{'s' if users_notified_tx != 1 else ''}."
            )

    async def __sse_block_event_user_proc(self, block_sse_result: BlockSSEResult, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult):
        block: Block = block_sse_result.block
        addr: AddrBase = addr_hist.addr

        sent = 0

        if block_sse_result.event == SSEBlockEvent.create:
            if addr_hist.mined:
                return await self.__sse_block_event_user_mined(block_sse_result.block, addr_hist, addr_hist_user)

        elif block_sse_result.event == SSEBlockEvent.mature:
            if addr_hist.mined:
                return await self.__sse_block_event_user_mined_matured(block_sse_result.block, addr_hist, addr_hist_user)

        if not sent:
            log.warning(f"Unprocessed BlockSSEResult for user {addr_hist_user.user_addr.user.tg_user_id} addr {str(addr)} block #{block.height}")

        return sent

    @staticmethod
    def staking_fmt(conf_block_stake: str, addr_hist: AddrHistResult) -> Optional[str]:
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

        return staking_tot

    @staticmethod
    def yield_block_tx_inout_values(block: Block, addr_hist: AddrHistResult, miner: bool = False) -> Generator[AttrDict, None, None]:
        addr: AddrBase = addr_hist.addr
        addr_str = str(addr)
        a = lambda a_: a_.get("addressHex", a_.get("address"))

        refund = 0

        for trxn in (addr.filter_tx(block) if not miner else [block.tx[1]]):
            txid = trxn.get("id")
            txno = block.info["transactions"].index(txid)
            fees = int(trxn.get("fees", 0))

            value_in = sum(
                int(inp.get("value", 0))
                for inp in trxn.get("inputs", [])
                if a(inp) == addr_str
            )

            value_out = sum(
                int(out.get("value", 0))
                for out in trxn.get("outputs", [])
                if a(out) == addr_str
            )

            # NOTE: contractSpends are duplicated in separate block TX.

            # fees is == -block.reward for tx 1 (and includes refunds to others)
            if txno == 1:
                fees = value_in - value_out  # out - in == actual reward to miner (and in < out), and/or any fee refunds.

                if addr_hist.mined and not miner:
                    # Include the refund as part of the block reward, because it is.
                    # Net fees are then not shown on related TX but this is the most sensible way.
                    fees = 0

            elif not value_in:
                # only TX inputs pay fees, this prevents display of tx fee total on receive,
                # which can be confusing because it doesn't include any refunds to the sender.
                fees = 0

            else:  # -- At this point, there is no real way to determine a particular address's fee contribution to the TX.
                pass

            txv = AttrDict(**trxn)

            txv.update(dict(
                total_recv=value_out - value_in,
                value_send=value_in,
                value_recv=value_out,
                fees=fees,
                n=txno,
            ))

            yield txv

            if miner:
                return

    async def __sse_block_event_user_mined(self, block: Block, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult) -> int:
        user_addr: UserAddrResult = addr_hist_user.user_addr
        user: UserBase = user_addr.user

        conf = user.info.get("conf", {})
        ua_conf = user_addr.info.get("conf", {})

        conf_block_notify = ua_conf.get("block", {}).get("notify", conf.get("block", {}).get("notify", "priv"))
        conf_block_notify_both = False

        if conf_block_notify == "hide":
            return 0

        if isinstance(conf_block_notify, int) and conf_block_notify > 0:
            conf_block_notify = -conf_block_notify
            conf_block_notify_both = True

        conf_block_stake = ua_conf.get("block", {}).get("stake", conf.get("block", {}).get("stake", "hide"))
        conf_block_bal = ua_conf.get("block", {}).get("bal", conf.get("block", {}).get("bal", "hide"))
        conf_block_utxo = ua_conf.get("block", {}).get("utxo", conf.get("block", {}).get("utxo", "show"))
        conf_block_total = ua_conf.get("block", {}).get("total", conf.get("block", {}).get("total", "hide"))

        balance_str = None

        if conf_block_bal == "show":
            balance = int(addr_hist.info_new.get("balance", 0))

            if balance:
                # currency = user.info.get("fiat", "USD")
                # fiat_value = self.bot.hydra_fiat_value(currency, balance, with_name=False)

                balance_str = (
                    f"<b>Balance:</b> {'{:,}'.format(round(Addr.decimal(balance), 2))} HYDRA"
                )

        staking_tot = EventManager.staking_fmt(conf_block_stake, addr_hist)

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
                utxo_str = "\n<b>"
                utxo_str += "Merged" if utxo_inp_cnt > utxo_out_cnt else "Updated" if utxo_inp_cnt == utxo_out_cnt else "Split"
                utxo_str += f"</b> {num2words(utxo_inp_cnt)} UTXO{'s' if utxo_inp_cnt != 1 else ''}"

                if utxo_inp_cnt != utxo_out_cnt:
                    utxo_str += f" into {num2words(utxo_out_cnt)}"

                utxo_str += f" with a total output of about {utxo_out_tot} HYDRA."
            else:  # == "show"
                utxo_str = f"<b>UTXOs:</b> +{utxo_out_tot} ({utxo_inp_cnt} ➔ {utxo_out_cnt})"

        # Determine how much of the total reward belongs to this address:
        #
        txv = list(txv for txv in EventManager.yield_block_tx_inout_values(block, addr_hist, miner=True))[0]
        reward = txv.total_recv

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
            f'<b>Reward:</b> <a href="{self.bot.rpcx.human_link("tx", block_tx["id"])}">+{reward}</a> HYDRA',
            f"<b>Value:</b> {value} @ <b>{price}</b>",
        ]

        if txv.fees and conf_block_notify_both:  # Adding conf_block_notify_both to ensure this is not normally shown.
            fee_str = "Refunds" if txv.fees < 0 else "Fees"  # Will always be < 0. But just in case.
            refunds = Addr.decimal(abs(txv.fees))
            refunds_value = await self.bot.hydra_fiat_value(currency, refunds, with_name=False)

            message.append(
                f"<b>{fee_str}:</b> {round(refunds, 2)} HYDRA ~ {refunds_value}"
            )

        if staking_tot is not None:
            message += [
                f"<b>Staking:</b> {staking_tot}",
            ]

        if utxo_str:
            message.append(utxo_str)

        blocks_mined = addr_hist.info_new.get("blocksMined", 0)

        if conf_block_total != "hide" and (user_addr.block_c or blocks_mined):
            if message[-1] != "":
                message.append("")

            if conf_block_total == "show":
                if user_addr.block_c:
                    message.append(
                        f"<b>Hydraverse blocks:</b> {user_addr.block_c}"
                    )

                if blocks_mined:
                    message.append(
                        f"<b>Total blocks minted:</b> {blocks_mined}"
                    )
            else:  # == "full"
                block_msg = ""

                if user_addr.block_c:
                    block_msg = f"This is your {num2words(user_addr.block_c, ordinal=True)} Hydraverse block"

                if blocks_mined:
                    if block_msg:
                        block_msg += " and the "
                    else:
                        block_msg = "This is the "

                    block_msg += f"{ordinal(blocks_mined)} block mined by this address."

                message.append(block_msg)

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
                f"Last block mined <b>{td_msg}</b> ago:\n<b>{tz_time}</b>"
            ]

        message.append(
            f"<b>{block_time.ctime()} {block_time.tzname()}</b>"
        )

        message = "\n".join(message)

        sent = await try_send_notify(self.bot.send_message(
            chat_id=conf_block_notify if isinstance(conf_block_notify, int) else user.tg_user_id,
            text=message,
            parse_mode="HTML"
        ))

        if conf_block_notify_both:
            sent += await try_send_notify(self.bot.send_message(
                chat_id=user.tg_user_id,
                text=message,
                parse_mode="HTML"
            ))

        if conf_block_bal == "full":
            await self.addr_show(user, user_addr, addr_hist, conf_block_notify, conf_block_notify_both)

        return sent

    async def __sse_block_event_user_mined_matured(self, block: Block, addr_hist: AddrHistResult, addr_hist_user: UserAddrHistResult) -> int:
        user_addr: UserAddrResult = addr_hist_user.user_addr
        user: UserBase = user_addr.user

        conf = user.info.get("conf", {})
        ua_conf = user_addr.info.get("conf", {})

        conf_block_mature = ua_conf.get("block", {}).get("mature", conf.get("block", {}).get("mature", "full"))
        conf_block_stake = "full"
        conf_block_notify = ua_conf.get("block", {}).get("notify", conf.get("block", {}).get("notify", "priv"))

        if conf_block_mature == "hide":
            return 0

        conf_block_notify_both = False

        if isinstance(conf_block_notify, int) and conf_block_notify > 0:
            conf_block_notify = -conf_block_notify
            conf_block_notify_both = True

        staking_tot = EventManager.staking_fmt(conf_block_stake, addr_hist)

        utxo_out_tot = 0

        block_tx = block.tx[1]

        for out in filter(lambda out_: out_.get("address") == addr_hist.addr.addr_hy, block_tx["outputs"]):
            value = int(out.get("value", 0))

            if value:
                utxo_out_tot += value

        utxo_out_tot = round(Addr.decimal(utxo_out_tot), 2)

        reward = round(Addr.decimal(block.info["reward"]), 2)

        message = [
            f'<b><a href="{self.bot.rpcx.human_link("address", str(addr_hist.addr))}">{user_addr.name}</a> '
            + f'block <a href="{self.bot.rpcx.human_link("block", block.height)}">#{block.height}</a> has matured!</b>\n',
            f'<b>Reward:</b> <a href="{self.bot.rpcx.human_link("tx", block_tx["id"])}">+{reward}</a> HYDRA',
            f"UTXOs: +{utxo_out_tot}",
        ]

        if staking_tot:
            message += [
                f"Staking: {staking_tot}",
            ]

        message = "\n".join(message)

        sent = await try_send_notify(self.bot.send_message(
            chat_id=conf_block_notify if isinstance(conf_block_notify, int) else user.tg_user_id,
            text=message,
            parse_mode="HTML"
        ))

        if conf_block_notify_both:
            sent += await try_send_notify(self.bot.send_message(
                chat_id=user.tg_user_id,
                text=message,
                parse_mode="HTML"
            ))

        if conf_block_mature == "full":
            await self.addr_show(user, user_addr, addr_hist, conf_block_notify, conf_block_notify_both)

        return sent

    async def __sse_block_event_proc_tx(self, block: Block, addr_hist: AddrHistResult) -> int:
        addr: AddrBase = addr_hist.addr
        addr_str = str(addr)

        addr_txes: Dict[int, AttrDict] = {}
        tokn_xfrs: Dict[str, Dict[str, List[AttrDict]]] = {}
        sent = 0

        for txv in EventManager.yield_block_tx_inout_values(block, addr_hist):
            txid = txv.get("id")

            token_transfers = txv.get("qrc20TokenTransfers", []) + txv.get("qrc721TokenTransfers", [])

            if txv.n == 1 and addr_hist.mined:
                # token_transfers is assumed to be empty.
                continue

            log.info(f"Block #{block.height} TX #{txv.n} Addr {addr_str}: value_send={txv.value_send} value_recv={txv.value_recv} fees={txv.fees}")

            for token_transfer in token_transfers:
                token_transfer = AttrDict(token_transfer)

                addr_send = token_transfer.get("fromHex", token_transfer.get("from", None))
                addr_recv = token_transfer.get("toHex", token_transfer.get("to", None))
                addr_smac = token_transfer.addressHex

                if "value" in token_transfer:
                    value_or_id = Addr.decimal(token_transfer.value, decimals=token_transfer.decimals)
                else:
                    value_or_id = int(token_transfer.tokenId, 16)

                token_tx = AttrDict(
                    name=token_transfer.name,
                    symbol=token_transfer.symbol,
                    value_or_id=value_or_id,
                    addr_send=addr_send,
                    addr_recv=addr_recv
                )

                if (addr_str == addr_smac and addr_send != addr_smac and addr_recv != addr_smac) or \
                        addr_str == addr_send or addr_str == addr_recv:

                    tokn_xfrs.setdefault(addr_smac, {}).setdefault(txid, []).append(token_tx)

            addr_txes[txv.n] = txv

        if len(addr_txes):
            total_recv = Addr.decimal(
                sum(addr_tx.value_recv for addr_tx in addr_txes.values()) -
                sum(addr_tx.value_send for addr_tx in addr_txes.values())
            )
            total_fees = Addr.decimal(sum(utx.fees for utx in addr_txes.values()))

            block_txes = AttrDict(
                txes=addr_txes,
                token_xfrs=tokn_xfrs,
                total_recv=total_recv,
                total_fees=total_fees
            )

            for user_hist in addr_hist.addr_hist_user:
                sent += await self.__sse_block_event_proc_tx_user(user_hist.user_addr, addr_hist, block, block_txes)

        return sent

    async def __sse_block_event_proc_tx_user(self, ua: UserAddrResult, addr_hist: AddrHistResult, block: Block, block_txes: AttrDict) -> int:
        u: UserBase = ua.user
        a: AddrBase = addr_hist.addr
        addr_str = str(a)

        conf = u.info.get("conf", {})
        ua_conf = u.info.get("conf", {})

        conf_block_tx = ua_conf.get("block", {}).get("tx", conf.get("block", {}).get("tx", "show"))

        if conf_block_tx == "hide":
            return 0

        conf_block_notify = ua_conf.get("block", {}).get("notify", conf.get("block", {}).get("notify", "priv"))
        conf_block_notify_both = False

        if isinstance(conf_block_notify, int) and conf_block_notify > 0:
            conf_block_notify = -conf_block_notify
            conf_block_notify_both = True

        txes: Dict[int, AttrDict] = block_txes.txes
        token_xfrs: Dict[str, Dict[str, List[AttrDict]]] = block_txes.token_xfrs

        if 1 in txes:
            if len(txes) > 1 and conf_block_tx != "full":
                del txes[1]

        txes_show = {tx.id: tx for tnxo, tx in txes.items() if tx.total_recv}

        txes_len = len(txes_show)

        message = [
            f"{addr_link(self.bot, a, ua.name)} has {num2words(txes_len) if txes_len > 1 else 'a'} new transaction{'s' if txes_len > 1 else ''}"
            + f" in block {self.block_link(block, f'#{block.height}')}!",
            "",
        ]

        total_recv: Decimal = block_txes.total_recv
        total_fees: Decimal = block_txes.total_fees

        if total_fees == -total_recv:
            total_recv += total_fees

        currency = u.info.get("fiat", "USD")
        total_recv_value = await self.bot.hydra_fiat_value(currency, abs(total_recv), with_name=False)

        if total_recv != 0:
            send_recv = "Receive" if total_recv > 0 else "Send"

            if txes_len == 1:
                send_recv = self.tx_link(tuple(txes_show.keys())[0], send_recv)

            send_recv = f"<b>{send_recv}:</b> {abs(total_recv)} HYDRA"
            send_recv += f" ~ {total_recv_value}"

            message.append(send_recv)

        if total_fees:
            fee_msg = "Fees" if total_fees > 0 else "Reward"

            if len(txes) == 1 and not total_recv:
                fee_msg = self.tx_link(tuple(txes.values())[0].id, fee_msg)

            fee_total_value = await self.bot.hydra_fiat_value(currency, abs(total_fees), with_name=False)

            message.append(
                f"<b>{fee_msg}:</b> {abs(total_fees)} HYDRA ~ {fee_total_value}"
            )

        if txes_len > 1:
            for txid, tx in txes_show.items():
                link_text = "Refund" if tx.n == 1 else f"TX {tx.n - 1}"
                tx_total_recv_dec = Addr.decimal(tx.total_recv)

                message.append(
                    f"<b>{self.tx_link(txid, link_text)}:</b> {'+' if tx_total_recv_dec > 0 else '-'}{abs(tx_total_recv_dec)}"
                )

        first_token = True

        for token_addr, token_in_txes_all in token_xfrs.items():
            for txid, token_in_txes in token_in_txes_all.items():
                for token_in_tx in token_in_txes:
                    is_nft = not isinstance(token_in_tx.value_or_id, Decimal)
                    txrx = "Send" if addr_str == token_in_tx.addr_send else "Receive" if addr_str == token_in_tx.addr_recv else "Transfer"
                    action = "Mint" if token_in_tx.addr_send is None else "Burn" if token_in_tx.addr_recv is None else txrx
                    action += " NFT" if is_nft else ""

                    if not is_nft:
                        value_str = f"<b>{self.tx_link(txid, action)}:</b> {token_in_tx.value_or_id} {addr_link_str(self.bot, token_addr, token_in_tx.symbol)}"
                    else:
                        value_str = f"<b>{self.tx_link(txid, action)}:</b> {addr_link_str(self.bot, token_addr, token_in_tx.symbol)} ID #{token_in_tx.value_or_id}"
                        # TODO: Maybe also get URI data from addr_hist.info_new.qrc721Balances[].uris[]

                    if token_in_tx.symbol == "LOC" and token_in_tx.value_or_id:
                        loc_fiat_value = await self.bot.locktrip_fiat_value(
                            currency,
                            token_in_tx.value_or_id,
                            with_name=total_recv == 0
                        )

                        value_str += f" ~ {loc_fiat_value}"

                    if first_token:
                        first_token = False

                        if message[-1] != "":
                            message.append("")

                    message.append(value_str)

        if message[-1] != "":
            message.append("")

        tz_time = u.user_time(datetime.utcfromtimestamp(block.info.get("timestamp", datetime.utcnow().timestamp())))

        message.append(
            f"<pre>{tz_time.ctime()} {tz_time.tzname()}</pre>"
        )

        message = "\n".join(message)

        sent = await try_send_notify(self.bot.send_message(
            chat_id=conf_block_notify if isinstance(conf_block_notify, int) else u.tg_user_id,
            text=message,
            parse_mode="HTML"
        ))

        if conf_block_notify_both:
            sent += await try_send_notify(self.bot.send_message(
                chat_id=u.tg_user_id,
                text=message,
                parse_mode="HTML"
            ))

        if conf_block_tx == "full":
            await self.addr_show(u, ua, addr_hist, conf_block_notify, conf_block_notify_both)

        return sent

    async def addr_show(self, u: UserBase, ua: UserAddrResult, ah: AddrHistResult, conf_notify: Union[int, str], conf_notify_both: bool):
        addr = Addr(
            info=ah.info_new,
            **AttrDict(ah.addr.dict())
        )

        await try_send_notify(
            addr_show(self.bot, conf_notify if isinstance(conf_notify, int) else u.tg_user_id, u, ua, addr)
        )

        if conf_notify_both:
            await try_send_notify(
                addr_show(self.bot, u.tg_user_id, u, ua, addr)
            )

    def block_link(self, block: Block, text: str) -> str:
        return f'<a href="{self.bot.rpcx.human_link("block", block.height)}">{text}</a>'

    def tx_link(self, txid: str, text: str) -> str:
        return f'<a href="{self.bot.rpcx.human_link("tx", txid)}">{text}</a>'


async def try_send_notify(coro) -> int:
    try:
        await coro
        return 1

    except aiogram.exceptions.TelegramForbiddenError as exc:
        log.warning(f"Unable to send notification: {exc}")

    except aiogram.exceptions.AiogramError as exc:
        log.warning(f"Unable to send notification: {exc}", exc_info=exc)
        # Recently seen: TelegramForbiddenError: Blocked by user

    return 0
