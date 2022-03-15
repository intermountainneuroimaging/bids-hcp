"""Unit tests for run_level.py"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from utils.helper_funcs import check_fmap_types, sanitize_gdcoeff_name


@pytest.mark.parametrize(
    "mock_fp, expected_fp",
    [
        ("a long walk/in the snow", "a_long_walk/in_the_snow"),
        ("simple/case", "simple/case"),
    ],
)
@patch("os.rename")
def test_sanitize_gd_coeff_name(mock_rename, mock_fp, expected_fp):
    test_out = sanitize_gdcoeff_name(mock_fp)
    assert test_out == expected_fp


def test_check_fmap_types_fails(caplog):
    mock_types = ["orangutan", "dolphin", "orangutan"]
    check_fmap_types(mock_types)
    assert "check your BIDS" in caplog.messages[0]


def test_check_fmap_types_succeeds():
    mock_types = ["apple", "apple", "apple"]
    test_out = check_fmap_types(mock_types)
    assert test_out == "apple"
