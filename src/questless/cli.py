# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Command-line entry point. Subcommands (run, replay, demo) arrive in later milestones."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from questless import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="questless", description="Emergent quests from living worlds."
    )
    parser.add_argument("--version", action="version", version=f"questless {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(f"questless {__version__}: engine not implemented yet (see docs/PLAN.md, milestone M1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
