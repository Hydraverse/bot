from decimal import Decimal
from math import floor
from typing import Union

from hydb.api import schemas


def ordinal(n: int) -> str:
    """Return the ordinated number, e.g. 1st.
    """
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


def fiat_value_decimal_from_price(price: Union[Decimal, str], value: Union[Decimal, int, str]) -> Decimal:
    raw_mul: Decimal = (Decimal(price) if not isinstance(price, Decimal) else price) * \
                       (schemas.Addr.decimal(value) if not isinstance(value, Decimal) else value)

    fiat_value: Decimal = raw_mul

    for exp in range(2, 9):
        # The resulting types of floor() and round() are actually Decimal.
        # noinspection PyTypeChecker
        fiat_value = round(
            floor(
                raw_mul
                * Decimal(10**exp)
            ) / Decimal(10**exp),
            2
        )

        if fiat_value != int(raw_mul):
            break

        # Not enough decimals to represent: continue

    return fiat_value
