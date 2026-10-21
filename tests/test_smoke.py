# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import questless
from questless.cli import main


def test_package_imports_with_version():
    assert questless.__version__.startswith("0.1.0")


def test_cli_runs(capsys):
    assert main([]) == 0
    assert "questless" in capsys.readouterr().out
