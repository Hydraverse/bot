"""Created by Halospace Foundation.
Support: @TheHydraverse
"""
from __future__ import annotations

from decimal import Decimal

from aiogram import Bot, Dispatcher, types
from attrdict import AttrDict
from datetime import timedelta

from hydra.rpc.explorer import ExplorerRPC
from hydra import log

from hydb.api.client import HyDbClient, schemas
from hydra.kc.prices import PriceClient

from hybot.util.conf import Config

from hybot.bot.hydra.data import HydraBotData


@Config.defaults
class HydraBot(Bot):
    _: HydraBot = None
    dp = Dispatcher()

    conf: AttrDict

    db: HyDbClient
    rpcx: ExplorerRPC
    evm: object  # type: EventManager

    prices: PriceClient
    coin: AttrDict

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

        self.coin = AttrDict(self.prices.kuku.get_currency(self.prices.coin))

        token = self.conf.token

        if not token:
            raise ValueError("Invalid or no token found in config")

        HydraBotData.init(self.db)

        self.rpcx = ExplorerRPC(mainnet=HydraBotData.SERVER_INFO.mainnet)

        self.evm = EventManager(self)

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


from hybot.bot.hydra.events import EventManager
