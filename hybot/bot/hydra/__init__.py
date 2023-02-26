"""Created by Halospace Foundation.
Bot Support @ <a href="t.me/TheHydraverse">The Hydraverse</a>.
"""
from __future__ import annotations

import asyncio
import sys

from decimal import Decimal
from typing import Coroutine, Optional, Union, Dict

from attrdict import AttrDict
from datetime import timedelta

from aiogram import F
import aiogram.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.filters import BaseFilter
from aiogram.types import Message

from hydra.rpc.explorer import ExplorerRPC
from hydra import log

from hydb.api.client import HyDbClient, schemas
from hydra.kc.prices import PriceClient

from hybot.util.conf import Config
from hybot.util.gomt import PriceClientGOMT
from hybot.util.misc import fiat_value_decimal_from_price_simple


@Config.defaults
class HydraBot(Bot):
    _: HydraBot = None
    dp: Dispatcher = Dispatcher()

    conf: AttrDict

    db: HyDbClient
    rpcx: ExplorerRPC
    evm: object  # type: EventManager

    price_client_map: Dict[str, PriceClient]

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

    def __new__(cls, db, shell=None, *args, **kwds):
        if cls._ is None:
            cls._ = super(HydraBot, cls).__new__(cls, *args, **kwds)

        return cls._

    def __hash__(self):
        return hash(self.conf.token)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __init__(self, db: HyDbClient, shell: Optional[Coroutine] = None):
        self.db = db
        self.conf = Config.get(HydraBot, defaults=True)

        # noinspection PyPep8Naming
        PriceClientKeyed = lambda sym: PriceClient(
            coin=sym,
            api_key=self.conf.kc_key,
            api_secret=self.conf.kc_sec,
            passphrase=self.conf.kc_psp
        )

        pc_hydra = PriceClientKeyed("HYDRA")
        pc_usdt = PriceClientKeyed("USDT")

        self.price_client_map = {
            "HYDRA": pc_hydra,
            "WHYDRA": pc_hydra,
            "LOC": PriceClientKeyed("LOC"),
            "USDT": pc_usdt,
            "DAI": PriceClientKeyed("DAI"),
            "GOMT": PriceClientGOMT(pc_usdt),
        }

        for symbol, pc in self.price_client_map.items():
            if symbol == "GOMT":
                continue

            pc._cache.expiry = timedelta(minutes=1 if symbol == "HYDRA" else 3)

        token = self.conf.token

        if not token:
            raise ValueError("Invalid or no token found in config")

        HydraBotData.init(self.db)

        self.rpcx = ExplorerRPC(mainnet=HydraBotData.SERVER_INFO.mainnet)

        if shell is None:
            self.evm = EventManager(self)
        else:
            @self.dp.startup()
            async def startup():
                await shell

        from . import \
            hello as cmd_hello, \
            tz as cmd_tz, \
            addr as cmd_addr, \
            delete as cmd_delete, \
            fiat as cmd_fiat, \
            conf as cmd_conf, \
            chain as cmd_chain

        async def chat_message_filter(message: Message) -> bool:
            return message.text is not None and len(str(message.text))

        self.dp.message.filter(chat_message_filter)

        @HydraBot.dp.message(F.text.lower().in_({"/hello", "/start", "/hi", "/help"}))
        async def hello(msg: types.Message):
            return await self.command(msg, cmd_hello.hello)

        @self.dp.message(F.text.startswith("/tz"))
        async def tz(msg: types.Message):
            return await self.command(msg, cmd_tz.tz)

        @self.dp.message(F.text.startswith("/DELETE"))
        async def delete(msg: types.Message):
            return await self.command(msg, cmd_delete.delete)

        @self.dp.message(F.text.startswith("/fiat").or_(F.text.startswith("/price")))
        async def fiat(msg: types.Message):
            log.warning(f"fiat command: {msg}")
            return await self.command(msg, cmd_fiat.fiat)

        @self.dp.message(F.text.startswith("/conf"))
        async def conf(msg: types.Message):
            return await self.command(msg, cmd_conf.conf)

        @self.dp.message(F.text.startswith("/chain"))
        async def chain(msg: types.Message):
            return await self.command(msg, cmd_chain.chain)

        # @self.dp.message()
        @self.dp.message(F.text.startswith("/addr").or_(F.text.startswith("/a")))
        async def addr_(msg: types.Message):
            return await self.command(msg, cmd_addr.addr)

        @self.dp.callback_query()
        async def process_callback(callback_query: types.CallbackQuery):
            if callback_query.data.startswith("refresh:") or callback_query.data.startswith("show:"):
                parts = callback_query.data.split(":")
                action = parts[0]
                user_pk, user_addr_pk, chat_id = map(int, parts[1:])

                return await self.show_addr(callback_query.message, user_pk, user_addr_pk, chat_id, refreshing=action == "refresh")

            elif callback_query.data == "remove":
                return await callback_query.message.delete_reply_markup()

            elif callback_query.data == "chain:refresh":
                return await cmd_chain.chain(self, callback_query.message, refresh=True)

        super().__init__(token, parse_mode="HTML")

    @staticmethod
    def main(db: HyDbClient):
        return HydraBot(db).run()

    async def fiat_value_of(self, symbol: str, currency: str, value: Union[Decimal, int, str], *, with_name=True) -> str:
        return await HydraBot.fiat_value(self.price_client_map[symbol], currency, value, with_name=with_name)

    async def fiat_value_dec_of(self, symbol: str, currency: str, value: Union[Decimal, int, str]) -> Decimal:
        return await HydraBot.fiat_value_decimal(self.price_client_map[symbol], currency, value)

    async def hydra_fiat_value(self, currency: str, value: Union[Decimal, int, str], *, with_name=True) -> str:
        return await HydraBot.fiat_value(self.price_client_map["HYDRA"], currency, value, with_name=with_name)

    async def hydra_fiat_value_dec(self, currency: str, value: Union[Decimal, int, str]) -> Decimal:
        return await HydraBot.fiat_value_decimal(self.price_client_map["HYDRA"], currency, value)

    def fiat_value_format(self, currency: str, fiat_value: Decimal, *, with_name=True) -> str:
        # noinspection StrFormat
        return self.price_client_map["HYDRA"].format(
            currency,
            '{:,}'.format(fiat_value),
            with_name=with_name
        )

    @staticmethod
    async def fiat_value(pc: PriceClient, currency: str, value: Union[Decimal, int, str], *, with_name=True) -> str:

        fiat_value = await HydraBot.fiat_value_decimal(pc, currency, value)

        # noinspection StrFormat
        return pc.format(
            currency,
            '{:,}'.format(fiat_value),
            with_name=with_name
        )

    @staticmethod
    async def fiat_value_decimal(pc: PriceClient, currency: str, value: Union[Decimal, int, str]) -> Decimal:
        price = await asyncio.get_event_loop().run_in_executor(
            executor=None,
            func=lambda: pc.price(currency, raw=True)
        )

        # The resulting types of floor() and round() are actually Decimal.
        # noinspection PyTypeChecker
        fiat_value: Decimal = fiat_value_decimal_from_price_simple(price, value)

        return fiat_value

    async def show_addr(self, msg: Message, user_pk: int, user_addr_pk: int, chat_id: int, refreshing: bool = True):

        ua: Optional[schemas.UserAddrFull] = await self.db.asyncc.user_addr_get(user_pk, user_addr_pk)

        reply_markup = msg.reply_markup

        if refreshing and reply_markup is not None:
            if reply_markup.inline_keyboard[0][0].callback_data == "-":
                return

            refresh_reply_markup = types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(text="♻", callback_data="-")
                ]]
            )

            try:
                await msg.edit_reply_markup(reply_markup=refresh_reply_markup)
            except aiogram.exceptions.TelegramBadRequest:
                pass
        else:
            if reply_markup is not None:
                await msg.delete_reply_markup()

            refresh_reply_markup = None

        if ua is None:
            return

        u: schemas.UserBase = ua.user

        from .addr import addr_show

        new_text = await addr_show(
            bot=self,
            chat_id=chat_id,
            u=u,
            ua=ua,
            render=refreshing
        )

        if not refreshing:
            return

        try:
            if refresh_reply_markup is not None:
                await msg.edit_text(text=new_text, reply_markup=refresh_reply_markup)
            else:
                await msg.edit_text(text=new_text)

        except aiogram.exceptions.TelegramBadRequest:
            pass

        if refresh_reply_markup is not None and reply_markup is not refresh_reply_markup:
            await asyncio.sleep(5)
            await msg.edit_reply_markup(reply_markup=reply_markup)

        return

    def run(self):
        return self.dp.run_polling(self)

    async def send_message(self, *args, **kwds) -> Message:
        while 1:
            try:
                return await super().send_message(*args, **kwds)
            except aiogram.exceptions.TelegramRetryAfter as ex:
                log.warning("Throttled: %s", ex)
                await asyncio.sleep(ex.retry_after)

    async def command(self, msg, fn, *args, **kwds):
        # noinspection PyBroadException
        try:
            return await fn(self, msg, *args, **kwds)
        except BaseException as error:
            try:
                await msg.answer(
                    f"Sorry, something went wrong.\n\n<pre>\n{error}\n</pre>",
                )
            except BaseException as inner_error:
                print("Error while sending error message (ignored):", inner_error)

            print(f"Error while processing message '{msg}':", error)

            if log.level() <= log.DEBUG:
                raise


from hybot.bot.hydra.data import HydraBotData
from hybot.bot.hydra.events import EventManager
