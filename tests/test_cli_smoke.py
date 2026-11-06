"""Дымовые тесты argparse CLI."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from scripts.onec_ops import build_parser


def test_root_help_exits_successfully():
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["--help"])

    assert error.value.code == 0


def test_create_ib_help_exits_successfully():
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["create-ib", "--help"])

    assert error.value.code == 0


def test_help_survives_output_encoding_without_cyrillic():
    environment = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    result = subprocess.run(
        [sys.executable, "-m", "scripts.onec_ops", "--help"],
        capture_output=True,
        env=environment,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert b"create-ib" in result.stdout
