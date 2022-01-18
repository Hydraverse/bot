import sys
import os

from setuptools import find_packages
from setuptools import setup

import hybot


# noinspection Assert
assert sys.version_info[0] == 3 and sys.version_info[1] >= 8, "This package requires Python 3.8 or newer"

setup(
    name="hybot",
    url="https://github.com/hydraverse/hybot",
    author="Halospace Foundation",
    author_email="contact@halospace.org",
    version=hybot.VERSION,
    description=hybot.__doc__,
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "halo-hypy",
        "sqlalchemy",
        "sqlalchemy-json",
        "psycopg2-binary",
        "alembic[tz]",
        "pyyaml",
        "fuzzywuzzy",
        "python-Levenshtein",
        "https://github.com/aiogram/aiogram/archive/refs/heads/dev-3.x.zip",
    ],
    entry_points={
        "console_scripts": [
            "hybot = hybot:Hybot.main"
        ]
    })
