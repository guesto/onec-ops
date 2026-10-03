"""Дымовые тесты argparse CLI."""

from __future__ import annotations

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
