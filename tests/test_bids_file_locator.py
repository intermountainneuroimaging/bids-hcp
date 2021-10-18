from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from flywheel_gear_toolkit import GearToolkitContext

from utils import set_gear_args
from utils.bids.bids_file_locator import bidsInput

# Check here for help on the class problem.
# https://stackoverflow.com/questions/28074697/how-do-i-mock-a-class-in-a-python-unit-test

# def test_bidsInput(mock_gtk_context):
#     mock_gtk_context.config_json = {"return": "something"}
#     with patch("utils.bids.bids_file_locator.run_level.get_analysis_run_level_and_hierarchy"):
#         test_bids = bidsInput(mock_gtk_context)
#     assert test_bids.config['return'] == 'something'
#     assert not test_bids.t2ws


class TestBids:
    @pytest.fixture(autouse=True)
    def init__(self, mock_gtk_context):
        mock_gtk_context.config_json = {"return": "something"}
        with patch(
            "utils.bids.bids_file_locator.run_level.get_analysis_run_level_and_hierarchy"
        ):
            self.test_bids = bidsInput(mock_gtk_context)
        self.test_bids.layout = MagicMock()
        self.test_bids.layout.get.return_value = [Path("a"), Path("b"), Path("c")]

    def test_bidsInputClass(self):
        """Did the TestBIds Class inherit the correct mock and initialize?"""
        assert self.test_bids.config["return"] == "something"
        assert not self.test_bids.t2ws

    def test_findT1ws_returnsT1ws(self, mock_gear_args):
        self.test_bids.find_t1ws(self)
        assert len(mock_gear_args.structural["raw_t1s"]) == 3


# def test_find_bids_files(mock_gtk_context):
#    with patch("utils.bids.bids_file_locator.run_level.get_analysis_run_level_and_hierarchy"):
#        test_bids = bidsInput(mock_gtk_context)

# test_bids.find_bids_files(mock_gear_args)
# assert mock_layout.call_count == 1
#
# def test_find_t1ws(self, mock_gear_args):
#     pass
#
# def test_find_t2ws(self):
#     pass
#
# def test_find_bolds(self):
#     pass
#
# def test_find_dwis(self):
#     pass
#
# def test_grab_BIDS_data(self):
#     pass
#
# def test_locate_scan_params(self):
#     pass
