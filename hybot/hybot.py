"""Hydra Bot Application.
"""
from __future__ import annotations
import os
from argparse import ArgumentParser
from typing import Optional, Coroutine

from attrdict import AttrDict

from hydra.app import HydraApp
from hydra.test import Test

from hydb.api.client import HyDbClient
from hydra.util.asyncc import AsyncMethods

from .bot.hydra import HydraBot
from hybot.util.conf import Config

VERSION = "0.0.1"

os.environ["HYPY_NO_RPC_ARGS"] = "1"


@Config.defaults
@HydraApp.register(name="hybot", desc="Halospace Hydra Bot", version=VERSION)
class Hybot(HydraApp):
    _: Hybot
    asyncc: AsyncMethods
    db: HyDbClient
    bot: Optional[HydraBot]
    conf: AttrDict

    CONF = {
        "bot": "HydraBot"
    }

    @staticmethod
    def app():
        return Hybot._

    @staticmethod
    def parser(parser: ArgumentParser):
        parser.add_argument("-s", "--shell", action="store_true", help="Drop to an interactive shell with DB and RPC access.")

    def __init__(self, *args, **kwds):
        Hybot._ = self
        self.asyncc = AsyncMethods(self)
        self.bot = None

        if not Config.exists():
            self.render_item("error", f"Default config created and needs editing at: {Config.APP_CONF}")
            Config.read(create=True)
            exit(-1)

        self.conf = Config.get(Hybot)

        self.db = HyDbClient()

        super().__init__(*args, **kwds)

    def run(self):
        # TO DO: make bot a list and fork for each.
        #   Complicates shell scenario however,
        #   so that will need to load differently.
        #

        bot = self.conf.get("bot", ...)

        if bot is ... or bot != "HydraBot":
            self.render(
                name="error",
                result=f"Unknown default bot class '{bot}' specified in: {Config.APP_CONF}" if bot is not ... else
                f"No bot class specified in: {Config.APP_CONF}"
            )

            exit(-2)

        if bot == "HydraBot":
            self.bot = HydraBot(
                db=self.db,
                shell=self.asyncc.shell() if self.args.shell else None
            )

        if self.bot:
            self.bot.run()

    def shell(self):
        import sys, traceback, code, asyncio
        db = self.db
        bot = self.bot

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def awaits(coro: Coroutine):
            loopp = asyncio.get_event_loop()

            if loopp.is_closed():
                loopp = asyncio.new_event_loop()
                asyncio.set_event_loop(loopp)

            task = loopp.create_task(coro)
            return loopp.run_until_complete(task)

        run = awaits

        code.interact(
            banner=f"Hydraverse Bot Shell:\n  db = {db}\n  bot = {bot}\n  run() to call with awaits.",
            exitmsg="",
            local=locals(),
        )
        exit(0)


@Test.register()
class HybotTest(Test):

    def test_0_hybot_runnable(self):
        self.assertHydraAppIsRunnable(Hybot, "-h")

