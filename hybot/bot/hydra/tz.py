from datetime import datetime
from aiogram import types
from fuzzywuzzy import fuzz
import pytz

from . import HydraBot
from ...data import User
from .user import HydraBotUser


async def tz(bot: HydraBot, msg: types.Message):
    u = await HydraBotUser.load(bot.db, msg, create=True, full=False)

    try:
        tz_cur = u.info.get("tz", "UTC")
        tz_new = str(msg.text).replace("/tz", "", 1).strip()

        if not tz_new:
            return await msg.answer(
                f"Hiya, <b>{msg.from_user.username}</b>!\n\n"
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

            for tz_name in pytz.all_timezones:
                if tz_name.lower() == search.lower():
                    found = 1
                    response = f"Exact match: {tz_name}\n"
                    break

                if fuzz.token_sort_ratio(search.lower(), tz_name.lower()) > 50:
                    response += f"{tz_name}\n"
                    found += 1

            if found == 0:
                response = "No matching time zones found."

            return await msg.answer(response)

        for tz_name in pytz.all_timezones:
            if tz_name.lower() == tz_new.lower():
                tz_new = tz_name

        if tz_new == tz_cur:
            return await msg.answer(
                f"Timezone is already <b>{tz_cur}</b>.\n"
                "Looks like you're right where you need to be!"
            )

        tz_new_loc = pytz.timezone(tz_new).localize(datetime.now(), is_dst=None).tzname()

        await User.update_info(bot.db, u.pkid, {
            "tz": tz_new,
        })

        await msg.answer(f"Time zone changed to <b>{tz_new} ({tz_new_loc})</b>\n\n")

    except pytz.UnknownTimeZoneError as error:
        await msg.answer(f"Sorry, that timezone is not valid.\n\n<b>{repr(error)}</b>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{error}</b>")
        raise
