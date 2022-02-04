from datetime import datetime
from aiogram import types
from fuzzywuzzy import fuzz
import pytz

from . import HydraBot
from .data import HydraBotData, schemas

TZ_ALL_LOWER = {tz.lower(): tz for tz in pytz.all_timezones}


async def tz(bot: HydraBot, msg: types.Message):
    u: schemas.User = await HydraBotData.user_load(bot.db, msg, create=True)

    try:
        tz_cur = u.info.get("tz", "UTC")
        tz_new = str(msg.text).replace("/tz", "", 1).strip().lower()

        if not tz_new:
            return await msg.answer(
                f"Your current time zone is <b>{tz_cur}</b>.\n\n"
                "Change your timezone with <b>/tz [Time Zone]</b>\n"
                "Find a timezone with <b>/tz find [search]</b>"
            )

        if tz_new.startswith("find "):
            search = tz_new.split("find ", 1)[1]

            if not search:
                return await msg.answer(
                    "Usage: <b>/tz find [search]</b>"
                )

            response = "Matching time zones:\n\n"
            found = 0

            for tz_name, tz_name_full in TZ_ALL_LOWER.items():
                if tz_name == search:
                    found = 1
                    response = f"Exact match: {tz_name}\n"
                    break

                if fuzz.token_sort_ratio(search, tz_name) > 50:
                    response += f"{tz_name_full}\n"
                    found += 1

            if found == 0:
                response = "No matching time zones found."

            return await msg.answer(response)

        for tz_name, tz_name_full in TZ_ALL_LOWER.items():
            if tz_name == tz_new:
                tz_new = tz_name_full

        if tz_new.lower() == tz_cur.lower():
            return await msg.answer(
                f"Timezone is already <b>{tz_cur}</b>.\n"
                "Looks like you're right where you need to be!"
            )

        tz_new_loc = pytz.timezone(tz_new).localize(datetime.now(), is_dst=None).tzname()

        await bot.db.asyncc.user_info_put(
            u,
            {
                "tz": tz_new,
            }
        )

        await msg.answer(f"Time zone changed to <b>{tz_new} ({tz_new_loc})</b>\n\n")

    except pytz.UnknownTimeZoneError as error:
        await msg.answer(f"Sorry, that timezone is not valid.\n\n<b><pre>{repr(error)}</pre></b>")

