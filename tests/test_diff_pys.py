"""The structural analysis has four major methods. Test each."""
import logging
import os.path as op
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fw_gear_hcp_diff import DiffPreprocPipeline
from utils import set_gear_args

log = logging.getLogger(__name__)


def test_basicDiffSetParams(mock_gear_args):
    """Are the parameters set, when there are no strange value cases?"""
    params = DiffPreprocPipeline.set_params(mock_gear_args)
    assert len(params) == 13


@patch("fw_gear_hcp_diff.DiffPreprocPipeline.exec_command")
@patch("fw_gear_hcp_diff.DiffPreprocPipeline.build_command_list")
@patch("fw_gear_hcp_diff.DiffPreprocPipeline.os.makedirs")
def test_executeDiff(mock_mk, mock_build, mock_exec, mock_gear_args):
    """Does the execution block build and run the command?
    Error handling is in the modality's main.py"""
    DiffPreprocPipeline.execute(mock_gear_args)
    mock_build.assert_called_once()
    mock_exec.assert_called_once()
