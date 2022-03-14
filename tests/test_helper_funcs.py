"""Unit tests for run_level.py"""

import logging
from unittest.mock import MagicMock, patch

import pytest

import utils.helper_funcs
from utils.helper_funcs import (
    check_fmap_types,
    check_intended_for_fmaps,
    sanitize_gdcoeff_name,
    set_gdcoeffs_file,
)


# Add parametrize for jload_vals
@patch("utils.helper_funcs.json.loads")
@patch("utils.helper_funcs.glob", return_value=["fmap1", "fmap2"])
def test_check_intended_for_fmaps(mock_glob, mock_jload):
    pass


# stub    mock_jload.return_value = jload_vals
# stub    check_intended_for_fmaps(mock_bids, '/a/random/dir', 'my_kind_of_scan')


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
