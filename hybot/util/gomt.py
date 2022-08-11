"""GOMT PriceClient shim.

Translates BitMart GOMT/USDT value into user currency value via KuCoin
PriceClient's USDT value data.
"""
from datetime import timedelta
from decimal import Decimal

from hydra.kc.prices import PriceClient
from hydra.rpc import BaseRPC
from hydra.util.tlru import TimedLRU

__all__ = "PriceClientGOMT", "GOMTRPC"

from hybot.util.misc import fiat_value_decimal_from_price


class GOMTRPC(BaseRPC):
    URL = "https://api-cloud.bitmart.com"
    PATH_TICKER = "/spot/v1/ticker?symbol=GOMT_USDT"

    def __init__(self):
        super().__init__(GOMTRPC.URL)

    @property
    def ticker(self):
        return super().get(path=GOMTRPC.PATH_TICKER).data.tickers[0]

    @property
    def last_price(self):
        return self.ticker.last_price


class PriceClientGOMT:
    pc_usdt: PriceClient

    _rpc: GOMTRPC
    _cache: TimedLRU[int, Decimal]

    def __init__(self, pc_usdt: PriceClient):
        self.pc_usdt = pc_usdt
        self.format = self.pc_usdt.format

        self._rpc = GOMTRPC()
        self._cache = TimedLRU(expiry=timedelta(minutes=5), cache=self.__gomt_price)

    def price(self, currency: str, *, raw=False, with_name=False) -> str:
        if currency not in self.pc_usdt.currencies:
            raise ValueError("Invalid currency.")

        gomt_usdt_price = self._cache[0]
        usdt_currc_price = Decimal(self.pc_usdt.price(currency, raw=True))
        value = gomt_usdt_price * usdt_currc_price

        # noinspection StrFormat
        return (
            str(value) if raw else
            fiat_value_decimal_from_price(usdt_currc_price, value)
        )

    def __gomt_price(self, dummy: int) -> Decimal:
        return Decimal(self._rpc.last_price)
