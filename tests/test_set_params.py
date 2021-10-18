import logging
import os.path as op
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from fw_gear_hcp_diff import hcpdiff_qc_mosaic
from fw_gear_hcp_func import hcpfunc_qc_mosaic
from fw_gear_hcp_struct import hcpstruct_qc_mosaic, hcpstruct_qc_scenes
from utils import set_gear_args

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    ("test_name", "test_method", "test_field"),
    [
        ("diff_mosaic", hcpdiff_qc_mosaic.set_params, 'diffusion["qc_params"]'),
        ("func_mosaic", hcpfunc_qc_mosaic.set_params, 'functional["qc_params"]'),
        (
            "struct_mosaic",
            hcpstruct_qc_mosaic.set_params,
            'structural["qc_mosaic_params"]',
        ),
        (
            "struct_scenes",
            hcpstruct_qc_scenes.set_params,
            'structural["qc_scene_params"]',
        ),
    ],
)
def test_set_params(test_name, test_method, test_field, mock_gear_args):
    """Difficult to test as the output is an amended dictionary. If one steps through,
    these tests run through the method and will return the test_field only if there are
    no encountered errors."""
    test_method(mock_gear_args)
    assert mock_gear_args.test_field  # Final line of the set_params method


@pytest.mark.parametrize(
    ("test_name", "test_method", "mock_popen", "test_response", "mock_rc"),
    [
        (
            "struct_mosaic",
            hcpstruct_qc_mosaic.execute,
            "fw_gear_hcp_struct.hcpstruct_qc_mosaic.sp.Popen",
            "What is it?",
            0,
        ),
        (
            "struct_mosaic_EXCEPTION",
            hcpstruct_qc_mosaic.execute,
            "fw_gear_hcp_struct.hcpstruct_qc_mosaic.sp.Popen",
            "",
            1,
        ),
        (
            "struct_scenes",
            hcpstruct_qc_scenes.execute,
            "fw_gear_hcp_struct.hcpstruct_qc_scenes.sp.Popen",
            "Dunno, but it's neat.",
            0,
        ),
        (
            "struct_scenes_EXCEPTION",
            hcpstruct_qc_scenes.execute,
            "fw_gear_hcp_struct.hcpstruct_qc_scenes.sp.Popen",
            "",
            1,
        ),
    ],
)
def test_execute_struct_qc(
    test_name, test_method, mock_popen, test_response, mock_rc, mock_gear_args, caplog
):
    caplog.set_level("DEBUG")
    with patch(mock_popen) as mock_run:
        proc_mock = mock.Mock()
        attrs = {
            "communicate.return_value": (test_response, "no error"),
            "returncode": mock_rc,
        }
        proc_mock.configure_mock(**attrs)
        mock_run.return_value = proc_mock
        test_method(mock_gear_args)

    if test_response:
        assert test_response in caplog.text
    else:
        assert "ERROR" in caplog.text


@pytest.mark.parametrize(
    ("test_name", "test_method", "mock_build", "mock_exec", "msg"),
    [
        (
            "func_qc_exec",
            hcpfunc_qc_mosaic.execute,
            "fw_gear_hcp_func.hcpfunc_qc_mosaic.build_command_list",
            "fw_gear_hcp_func.hcpfunc_qc_mosaic.exec_command",
            "Functional QC",
        ),
        (
            "diff_qc_exec",
            hcpdiff_qc_mosaic.execute,
            "fw_gear_hcp_diff.hcpdiff_qc_mosaic.build_command_list",
            "fw_gear_hcp_diff.hcpdiff_qc_mosaic.exec_command",
            "Diffusion QC",
        ),
    ],
)
def test_execute_others_qc(
    test_name, test_method, mock_build, mock_exec, msg, mock_gear_args, caplog
):
    caplog.set_level(logging.DEBUG)
    with patch(mock_build):
        with patch(mock_exec) as mock_run:
            test_method(mock_gear_args)
    assert msg in caplog.text
    mock_run.assert_called_once()
