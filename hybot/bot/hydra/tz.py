from datetime import datetime
from aiogram import types
from fuzzywuzzy import fuzz
import pytz

from . import HydraBot


# noinspection PyProtectedMember
async def tz(msg: types.Message):
    u = await HydraBot._.db.user_load_or_create(msg.from_user.id)

    try:
        tz_cur = u.info.get("tz", None)
        tz_new = str(msg.text).replace("/tz", "", 1).strip()

        if not tz_new:
            return await msg.answer(
                f"Hiya, <b>{u.info.nick}</b>!\n\n"
                f"Your current time zone is <b>{u.info.tz}</b>.\n\n"
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
                if fuzz.token_sort_ratio(search, tz_name) > 66:
                    response += f"{tz}\n"
                    found += 1

            if found == 0:
                response = "No matching time zones found."

            return await msg.answer(response)

        if tz_new == tz_cur:
            return await msg.answer(
                f"Timezone is already <b>{tz_cur}</b>.\n"
                "Looks like you're right where you need to be!"
            )

        tz_new_loc = pytz.timezone(tz_new).localize(datetime.now(), is_dst=None).tzname()

        await HydraBot._.db.user_update_info(msg.from_user.id, {
            "tz": tz_new,
        })

        await msg.answer(f"Time zone changed to <b>{tz_new} ({tz_new_loc})</b>\n\n")

    except pytz.UnknownTimeZoneError as error:
        await msg.answer(f"Sorry, that timezone is not valid.\n\n<b>{repr(error)}</b>")

    except Exception as error:
        await msg.answer(f"Sorry, something went wrong.\n\n<b>{error}</b>")
        raise
