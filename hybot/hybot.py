"""Hydra Bot Application.
"""
import os
from argparse import ArgumentParser

from hydra.app import HydraApp
from hydra.test import Test

from hydb.api.client import HyDbClient, schemas
from .bot.hydra import HydraBot
from hybot.util.conf import Config

VERSION = "0.0.1"

os.environ["HYPY_NO_RPC_ARGS"] = "1"


@Config.defaults
@HydraApp.register(name="hybot", desc="Halospace Hydra Bot", version=VERSION)
class Hybot(HydraApp):
    db: HyDbClient

    CONF = {
        "bot": "HydraBot"
    }

    @staticmethod
    def parser(parser: ArgumentParser):
        parser.add_argument("-s", "--shell", action="store_true", help="Drop to an interactive shell with DB and RPC access.")

    def run(self):
        if not Config.exists():
            self.render_item("error", f"Default config created and needs editing at: {Config.APP_CONF}")
            Config.read(create=True)
            exit(-1)

        hybot_conf = Config.get(Hybot)

        bot = hybot_conf.get("bot", ...)

        if bot is ... or bot != "HydraBot":
            self.render(
                name="error",
                result=f"Unknown default bot class '{hybot_conf.bot}' specified in: {Config.APP_CONF}" if bot is not ... else
                       f"No bot class specified in: {Config.APP_CONF}"
            )

            exit(-2)

        self.db = HyDbClient()

        if self.args.shell:
            return self.shell()

        if bot == "HydraBot":
            HydraBot.main(self.db)

    # noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyBroadException
    def shell(self):
        import sys, traceback, code
        db = self.db
        code.interact(
            banner=f"Hydraverse Bot Shell:\n  db = {db}",
            exitmsg="",
            local=locals(),
        )
        exit(0)


@Test.register()
class HybotTest(Test):

    def test_0_hybot_runnable(self):
        self.assertHydraAppIsRunnable(Hybot, "-h")

