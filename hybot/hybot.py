"""Hydra Bot Application.
"""
from argparse import ArgumentParser

from hydra.app import HydraApp
from hydra.rpc import HydraRPC
from hydra.test import Test

from .bot.hydra import HydraBot
from .conf import Config

VERSION = "0.0.1"


@Config.defaults
@HydraApp.register(name="hybot", desc="Halospace Hydra Bot", version=VERSION)
class Hybot(HydraApp):

    CONF = {
        "bot": "HydraBot"
    }

    @staticmethod
    def parser(parser: ArgumentParser):
        pass

    def render_item(self, name: str, item):
        return self.render(result=HydraRPC.Result({name: item}), name=name)

    def run(self):
        if not Config.exists():
            self.render_item("error", f"Default config created and needs editing at: {Config.APP_CONF}")
            Config.read(create=True)
            exit(-1)

        hybot_conf = Config.get(Hybot)

        bot = hybot_conf.get("bot", ...)

        if bot is ... or bot != "HydraBot":
            self.render_item(
                "error",
                f"Unknown default bot class '{hybot_conf.bot}' specified in: {Config.APP_CONF}"
                if bot is not ... else
                f"No bot class specified in: {Config.APP_CONF}")
            exit(-2)

        if bot == "HydraBot":
            HydraBot.main(self.rpc)


@Test.register()
class HybotTest(Test):

    def test_0_hybot_runnable(self):
        self.assertHydraAppIsRunnable(Hybot, "-h")

    def test_1_hybot_run_default(self):
        self.assertHydraAppIsRunnable(Hybot)
