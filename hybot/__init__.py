"""Hydra Bot.
"""
from argparse import ArgumentParser

from hydra.app import HydraApp
from hydra.test import Test

VERSION = "0.0.1"


@HydraApp.register(name="hybot", desc="Halospace Hydra Bot", version=VERSION)
class Hybot(HydraApp):

    @staticmethod
    def parser(parser: ArgumentParser):
        pass

    def run(self):
        print("hybot", VERSION)


@Test.register()
class HybotTest(Test):

    def test_0_hybot_runnable(self):
        self.assertHydraAppIsRunnable(Hybot, "-h")

    def test_1_hybot_run_default(self):
        self.assertHydraAppIsRunnable(Hybot)
