"""The functional analysis has two major methods. Test each."""
import logging
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fw_gear_hcp_func import (
    GenericfMRISurfaceProcessingPipeline,
    GenericfMRIVolumeProcessingPipeline,
)
from utils import set_gear_args

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "test_name, test_fn, num_params, mock_babel",
    [
        (
            "vol_setParams",
            GenericfMRIVolumeProcessingPipeline.set_params,
            21,
            "GenericfMRIVolumeProcessingPipeline",
        ),
        (
            "surf_setParams",
            GenericfMRISurfaceProcessingPipeline.set_params,
            9,
            "GenericfMRISurfaceProcessingPipeline",
        ),
    ],
)
def test_basicSetParams(test_name, test_fn, num_params, mock_babel, mock_gear_args):
    """Are the parameters set, when there are no strange value cases?"""
    with patch("fw_gear_hcp_func." + mock_babel + ".nibabel.load") as babel:
        babel.return_value.get_header.return_value.get_zooms.return_value = [1, 2, 3]
        params = test_fn(mock_gear_args)
    assert len(params) == num_params


@pytest.mark.parametrize(
    "test_name, test_fn, mocked_exec, other_mocks",
    [
        (
            "vol_exec",
            GenericfMRIVolumeProcessingPipeline.execute,
            "fw_gear_hcp_func.GenericfMRIVolumeProcessingPipeline.exec_command",
            "fw_gear_hcp_func.GenericfMRIVolumeProcessingPipeline.build_command_list",
        ),
        (
            "surf_exec",
            GenericfMRISurfaceProcessingPipeline.execute,
            "fw_gear_hcp_func.GenericfMRISurfaceProcessingPipeline.exec_command",
            "fw_gear_hcp_func.GenericfMRISurfaceProcessingPipeline.build_command_list",
        ),
    ],
)
@patch("fw_gear_hcp_func.GenericfMRIVolumeProcessingPipeline.os.makedirs")
def test_execute(mock_mk, test_name, test_fn, mocked_exec, other_mocks, mock_gear_args):
    """Does the execution block build and run the command?
    Error handling is in the modality's main.py"""
    with patch(other_mocks):
        with patch(mocked_exec) as me:
            test_fn(mock_gear_args)
    me.assert_called_once()
