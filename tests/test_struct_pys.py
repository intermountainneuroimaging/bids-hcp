"""The structural analysis has four major methods. Test each."""
import logging
import os.path as op
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fw_gear_hcp_struct import FreeSurfer, PostFreeSurfer, PostProcessing, PreFreeSurfer
from utils import set_gear_args

log = logging.getLogger(__name__)

# Set params
def test_basicPreFSsetParams_brainSizeCatch(mock_gear_args, caplog):
    """Set the params for PreFS analysis and finds the override for brain size?"""
    caplog.set_level(logging.INFO)
    with patch(
        "fw_gear_hcp_struct.PreFreeSurfer.gear_arg_utils.query_json", return_value=1
    ):
        params = PreFreeSurfer.set_params(mock_gear_args)
    assert len(params) == 25
    assert "human brains have a diameter larger than 1 cm" in caplog.text.lower()
    assert "echodiff set" in caplog.text.lower()


def test_prefsSetParams_missingImgs(mock_gear_args, caplog):
    mock_gear_args.structural.pop("raw_t2s", None)
    with pytest.raises(SystemExit):
        with patch(
            "fw_gear_hcp_struct.PreFreeSurfer.gear_arg_utils.query_json", return_value=1
        ):
            params = PreFreeSurfer.set_params(mock_gear_args)
    assert "unable to locate" in caplog.text.lower()


def test_prefsSetParams_oddCases(mock_gear_args, caplog):
    caplog.set_level(logging.INFO)
    mock_gear_args.structural.update(
        {
            "raw_t1s": ["one_t1", "blue_t1"],
            "t1_sample_spacing": "NONE",
            "t2_sample_spacing": "NONE",
            "avgrdcmethod": "something",
            "echodiff": 0.01,
        }
    )
    mock_gear_args.common.update({"gdcoeffs": "accounted_for"})
    with patch(
        "fw_gear_hcp_struct.PreFreeSurfer.gear_arg_utils.query_json", return_value=None
    ):
        params = PreFreeSurfer.set_params(mock_gear_args)
    assert "more than one t1" in caplog.text.lower()
    assert params["t1"] == "one_t1"
    assert params["avgrdcmethod"] == "NONE"
    assert "echodiff values between 0.1 and 10.0 milliseconds" in caplog.text.lower()


def test_basicFSsetParams_missingFiles(mock_gear_args, caplog):
    """Files are missing in this test, partially dues to test setup, partially to test that the method will report the error."""
    caplog.set_level(logging.INFO)
    params = FreeSurfer.set_params(mock_gear_args)
    assert len(params) == 5
    assert "files were not found" in caplog.text.lower()


def test_basicPostFSparams_smooth(mock_gear_args):
    """There are no messages in the method. Test that the params are set."""
    with patch(
        "fw_gear_hcp_struct.PostFreeSurfer.glob",
        return_value=["fake/elephant/91282_Greyordinates/dir"],
    ):
        params = PostFreeSurfer.set_params(mock_gear_args)
    assert len(params) == 11


def test_basicPostProcParams_smooth(mock_gear_args):
    """There is nothing to this method. Check the single line."""
    PostProcessing.set_params(mock_gear_args)
    assert mock_gear_args.structural["metadata"] == {}


# Execute
@pytest.mark.parametrize(
    "test_name, test_fn, mocked_exec, other_mocks",
    [
        (
            "postproc_exec",
            PostProcessing.execute,
            "fw_gear_hcp_struct.PostProcessing.exec_command",
            "fw_gear_hcp_struct.PostProcessing.process_aseg_csv",
        ),
        (
            "FS_exec",
            FreeSurfer.execute,
            "fw_gear_hcp_struct.FreeSurfer.exec_command",
            "fw_gear_hcp_struct.FreeSurfer.build_command_list",
        ),
        (
            "PostFS_exec",
            PostFreeSurfer.execute,
            "fw_gear_hcp_struct.PostFreeSurfer.exec_command",
            "fw_gear_hcp_struct.PostFreeSurfer.build_command_list",
        ),
    ],
)
def test_execute(test_name, test_fn, mocked_exec, other_mocks, mock_gear_args):
    with patch(other_mocks):
        with patch(mocked_exec) as me:
            test_fn(mock_gear_args)
    me.assert_called_once()


@patch("fw_gear_hcp_struct.PreFreeSurfer.exec_command")
@patch(
    "fw_gear_hcp_struct.PreFreeSurfer.build_command_list",
    return_value=["commands", "to", "be", "run"],
)
@patch("fw_gear_hcp_struct.PreFreeSurfer.os.makedirs")
def test_executePreFS_works(mock_mk, mock_build, mock_exec, mock_gear_args, caplog):
    PreFreeSurfer.execute(mock_gear_args)
    mock_exec.assert_called_once()


@patch("fw_gear_hcp_struct.PreFreeSurfer.exec_command")
@patch(
    "fw_gear_hcp_struct.PreFreeSurfer.build_command_list",
    return_value=["commands", "to", "be", "run"],
)
@patch("fw_gear_hcp_struct.PreFreeSurfer.os.makedirs")
def test_executePreFs_errors(mock_mk, mock_build, mock_exec, mock_gear_args, caplog):
    caplog.set_level(logging.INFO)
    mock_exec.side_effect = RuntimeError("Oops")
    try:
        PreFreeSurfer.execute(mock_gear_args)
    except RuntimeError:
        assert True
    mock_build.assert_called_once()


# PostProcessing special methods


def test_setMetadataFromCsv_smooth(mock_gear_args):
    csv = op.join(op.dirname(op.abspath(__file__)), "data/test_aseg_stats_vol_mm3.csv")
    PostProcessing.set_metadata_from_csv(mock_gear_args, csv)
    assert (
        "Measure:volume"
        in mock_gear_args.structural["metadata"]["analysis"]["info"].keys()
    )


@patch("fw_gear_hcp_struct.PostProcessing.exec_command")
@patch("fw_gear_hcp_struct.PostProcessing.set_metadata_from_csv")
def test_executePreFS_works(mock_set, mock_exec, mock_gear_args):
    PostProcessing.execute(mock_gear_args)
    assert mock_exec.call_count == 6  # exec_command called an extra time before loop
    assert mock_set.call_count == 5
