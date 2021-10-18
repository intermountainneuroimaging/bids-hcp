"""Test each of the _utils.py"""
import logging
import os.path as op
from unittest import mock
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fw_gear_hcp_diff import diff_utils
from fw_gear_hcp_func import func_utils
from fw_gear_hcp_struct import struct_utils
from utils import set_gear_args

log = logging.getLogger(__name__)


@patch("fw_gear_hcp_struct.struct_utils.sp.Popen")
def test_get_FS_version_succeeds(mock_popen, mock_gear_args):
    """Test if the version number of FreeSurfer can be detected."""
    mock_result = mock.Mock()
    attrs = {"communicate.return_value": ("freesurfer -v 4 -other output", "-")}
    mock_result.configure_mock(**attrs)
    mock_popen.return_value = mock_result
    version = struct_utils.get_freesurfer_version(mock_gear_args)
    assert int(version) == 4


def test_struct_configs_to_export_succeeds(mock_gear_args):
    """Test that a dictionary and filepath are created to store the configurations.
    (The configs_to_export methods differ slightly between modality.)"""
    hcpstruct_config, hcpstruct_config_filename = struct_utils.configs_to_export(
        mock_gear_args
    )

    assert len(hcpstruct_config["config"].keys()) == 5
    assert "/" in hcpstruct_config_filename


@patch("fw_gear_hcp_func.func_utils.glob.glob", return_value=["/looky/here/a/nii.gz"])
def test_remove_intermediate_files_logsFailures(mock_glob, mock_gear_args, caplog):
    """Test that the exceptions will be recorded if the files to be deleted do not exist."""
    caplog.set_level(logging.INFO)
    func_utils.remove_intermediate_files(mock_gear_args)
    assert len(caplog.records) == 3


def test_func_configs_to_export_succeeds(mock_gear_args):
    """Test that a dictionary and filepath are created to store the configurations for
    functional utilities."""
    hcpfunc_config, hcpfunc_config_filename = func_utils.configs_to_export(
        mock_gear_args
    )

    assert len(hcpfunc_config["config"].keys()) == 5
    assert "json" in hcpfunc_config_filename


def test_dwi_configs_to_export_succeeds(mock_gear_args):
    """Test that a dictionary and filepath are created to store the configurations for
    diffusion utilities."""
    hcpdiff_config, hcpdiff_config_filename = diff_utils.configs_to_export(
        mock_gear_args
    )
    assert len(hcpdiff_config["config"].keys()) == 3
    assert (
        op.basename(hcpdiff_config_filename)
        == "sub-George_is_a_monkey_hcpdiff_config.json"
    )
