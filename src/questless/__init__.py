# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""QUESTLESS: emergent quests from living worlds."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("questless")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0+unknown"

from questless.api import Simulation  # noqa: E402  (needs __version__ defined first)

__all__ = ["Simulation", "__version__"]
