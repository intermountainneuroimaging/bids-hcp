"""Test each of the _main.py"""
import logging
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fw_gear_hcp_diff import diff_main
from fw_gear_hcp_func import func_main
from fw_gear_hcp_struct import struct_main
from utils import set_gear_args

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "test_name,test_path,test_msg",
    [
        ("invalid", "", "valid FreeSurfer license must be present"),
        ("valid", "/found/a/path/to/FS", "FreeSurfer installed"),
    ],
)
def test_fs_installed(
    test_name, test_path, test_msg, common_mocks, mock_gear_args, caplog
):
    """
    FreeSurfer must be installed. Test both cases where FS is and is not on the path
    """
    (
        mock_run,
        mock_exit,
        mock_copy,
        mock_results,
        mock_zip,
        mock_export,
    ) = common_mocks("struct")
    mock_run.return_value.stdout = test_path.encode("utf-8")
    caplog.set_level(logging.DEBUG)
    struct_main.check_FS_install(mock_gear_args)
    assert test_msg in caplog.text
    if test_name == "valid":
        mock_export.assert_called_once()
        assert mock_run.call_count == 2
    else:
        mock_exit.assert_called()


@pytest.mark.parametrize(
    ("test_name, test_mod, test_fn, method"),
    [
        (
            "preFS",
            "struct",
            struct_main.run_preFS,
            "fw_gear_hcp_struct.struct_main.PreFreeSurfer",
        ),
        (
            "FS",
            "struct",
            struct_main.run_FS,
            "fw_gear_hcp_struct.struct_main.FreeSurfer",
        ),
        (
            "fmriVol",
            "func",
            func_main.run_fmri_vol,
            "fw_gear_hcp_func.func_main.GenericfMRIVolumeProcessingPipeline",
        ),
        (
            "fmriSurf",
            "func",
            func_main.run_fmri_surf,
            "fw_gear_hcp_func.func_main.GenericfMRISurfaceProcessingPipeline",
        ),
        (
            "diffusion",
            "diff",
            diff_main.run_diffusion,
            "fw_gear_hcp_diff.diff_main.DiffPreprocPipeline",
        ),
    ],
)
def test_runMethod_works(
    test_name, test_mod, test_fn, method, common_mocks, mock_gear_args, caplog
):
    """Test whether the mocked function would run if there were no errors in set up"""
    common_mocks(test_mod)
    mock_gear_args.common["errors"] = []
    with patch(method) as mock_method:
        test_fn(mock_gear_args)
    mock_method.set_params.assert_called_once()
    mock_method.execute.assert_called_once()


@patch("fw_gear_hcp_struct.struct_main.results.cleanup")
@patch("fw_gear_hcp_struct.struct_main.PostProcessing")
@patch("fw_gear_hcp_struct.struct_main.PostFreeSurfer")
def test_runpostFS_works(mock_postFS, mock_post_proc, mock_results, mock_gear_args):
    """Test whether postFreeSurfer would run if there were no errors in set up"""
    struct_main.run_postFS(mock_gear_args)
    mock_postFS.set_params.assert_called_once()
    mock_postFS.execute.assert_called_once()
    mock_post_proc.set_params.assert_called_once()
    mock_post_proc.execute.assert_called_once()
    assert mock_results.call_count == 0


@pytest.mark.parametrize(
    ("test_name, test_mod, test_fn, method"),
    [
        (
            "preFS",
            "struct",
            struct_main.run_preFS,
            "fw_gear_hcp_struct.struct_main.PreFreeSurfer",
        ),
        (
            "FS",
            "struct",
            struct_main.run_FS,
            "fw_gear_hcp_struct.struct_main.FreeSurfer",
        ),
        (
            "postFS",
            "struct",
            struct_main.run_postFS,
            "fw_gear_hcp_struct.struct_main.PostFreeSurfer",
        ),
        (
            "fmriVol",
            "func",
            func_main.run_fmri_vol,
            "fw_gear_hcp_func.func_main.GenericfMRIVolumeProcessingPipeline",
        ),
        (
            "fmriSurf",
            "func",
            func_main.run_fmri_surf,
            "fw_gear_hcp_func.func_main.GenericfMRISurfaceProcessingPipeline",
        ),
        (
            "diffusion",
            "diff",
            diff_main.run_diffusion,
            "fw_gear_hcp_diff.diff_main.DiffPreprocPipeline",
        ),
    ],
)
def test_runMethod_paramsFail(
    test_name, test_mod, test_fn, method, common_mocks, mock_gear_args, caplog
):
    """Test whether the mocked function would run if there are errors during the parameter set up."""
    common_mocks(test_mod)
    caplog.set_level(logging.DEBUG)
    with patch(method) as mock_method:
        mock_method.set_params.side_effect = Exception()
        test_fn(mock_gear_args)

    mock_method.set_params.assert_called_once()
    assert mock_method.execute.call_count == 0
    assert len(mock_gear_args.common["errors"]) == 1


@pytest.mark.parametrize(
    ("test_name, test_mod, test_fn, method"),
    [
        (
            "preFS",
            "struct",
            struct_main.run_preFS,
            "fw_gear_hcp_struct.struct_main.PreFreeSurfer",
        ),
        (
            "FS",
            "struct",
            struct_main.run_FS,
            "fw_gear_hcp_struct.struct_main.FreeSurfer",
        ),
        (
            "postFS",
            "struct",
            struct_main.run_postFS,
            "fw_gear_hcp_struct.struct_main.PostFreeSurfer",
        ),
        (
            "fmriVol",
            "func",
            func_main.run_fmri_vol,
            "fw_gear_hcp_func.func_main.GenericfMRIVolumeProcessingPipeline",
        ),
        (
            "fmriSurf",
            "func",
            func_main.run_fmri_surf,
            "fw_gear_hcp_func.func_main.GenericfMRISurfaceProcessingPipeline",
        ),
        (
            "diffusion",
            "diff",
            diff_main.run_diffusion,
            "fw_gear_hcp_diff.diff_main.DiffPreprocPipeline",
        ),
    ],
)
def test_runMethod_execFails(
    test_name, test_mod, test_fn, method, common_mocks, mock_gear_args, caplog
):
    """Test whether the mocked function would run if there are errors during the execution of the algorithm."""
    mock_run, mock_exit, mock_copy, mock_results, mock_zip, mock_export = common_mocks(
        test_mod
    )
    caplog.set_level(logging.DEBUG)
    with patch(method) as mock_method:
        mock_method.execute.side_effect = Exception()
        rc = test_fn(mock_gear_args)

    mock_method.set_params.assert_called_once()
    mock_method.execute.assert_called_once()
    mock_results.call_count >= 1
    assert rc == 1
    if test_name == "FS":
        mock_zip.assert_called_once()
        mock_copy.assert_called_once()


@pytest.mark.parametrize(
    ("test_mod", "test_fn"),
    [
        ("struct", struct_main.run_struct_qc),
        ("func", func_main.run_func_qc),
        ("diff", diff_main.run_diff_qc),
    ],
)
def test_runQc_throwsException(test_mod, test_fn, qc_mocks, mock_gear_args, caplog):
    """
    If the final command in the try block fails, do you get the logs and sys.exit?
    """
    mock_results, mock_exit, mock_scene, mock_mosaic, mock_results_zip = qc_mocks(
        test_mod
    )
    mock_mosaic.execute.side_effect = Exception()
    mock_gear_args.common.update(
        {"scan_type": "xray", "exclude_from_output": "why_would_you_do_that"}
    )
    test_fn(mock_gear_args)

    mock_mosaic.set_params.assert_called_once()
    if test_mod == "struct":
        mock_scene.execute.assert_called_once()
    assert test_mod in caplog.text.lower()
    assert "ERROR" in caplog.records[0].levelname
    mock_results.call_count >= 1


@patch("fw_gear_hcp_struct.struct_main.run_struct_qc", return_value=0)
@patch("fw_gear_hcp_struct.struct_main.run_postFS", return_value=0)
@patch("fw_gear_hcp_struct.struct_main.run_FS", return_value=0)
@patch("fw_gear_hcp_struct.struct_main.run_preFS", return_value=0)
@patch("fw_gear_hcp_struct.struct_main.check_FS_install", return_value=0)
def test_struct_runs(
    mock_install, mock_pre, mock_fs, mock_post, mock_qc, common_mocks, mock_gear_args
):
    common_mocks("struct")
    struct_main.run(mock_gear_args)
    mock_install.assert_called_once()
    mock_pre.assert_called_once()
    mock_fs.assert_called_once()
    mock_post.assert_called_once()
    mock_qc.assert_called_once()


@patch("fw_gear_hcp_func.func_main.helper_funcs")
@patch("fw_gear_hcp_func.func_main.run_func_qc", return_value=0)
@patch("fw_gear_hcp_func.func_main.run_fmri_surf", return_value=0)
@patch("fw_gear_hcp_func.func_main.run_fmri_vol", return_value=0)
@patch("fw_gear_hcp_func.func_main.set_func_args_list", return_value=0)
@patch("fw_gear_hcp_func.func_main.set_func_args_single_file", return_value=0)
def test_func_runs(
    mock_sf, mock_list, mock_vol, mock_surf, mock_qc, _, common_mocks, mock_gear_args
):
    common_mocks("func")
    mock_bids = MagicMock()
    setattr(mock_bids, "layout", {"some_number": "of_func_files"})
    mock_gear_args.functional.update({"dcmethod": "correct_something"})

    func_main.run(mock_gear_args, mock_bids)
    assert mock_sf.call_count == len(mock_gear_args.functional["fmri_timecourse_all"])
    mock_vol.assert_called_once()
    mock_surf.assert_called_once()
    mock_qc.assert_called_once()


@patch("fw_gear_hcp_diff.diff_main.run_diff_qc", return_value=0)
@patch("fw_gear_hcp_diff.diff_main.run_diffusion", return_value=0)
def test_diff_runs(mock_diff, mock_qc, common_mocks, mock_gear_args):
    common_mocks("diff")

    with patch("fw_gear_hcp_diff.diff_main.helper_funcs.run_struct_zip_setup") as x:
        diff_main.run(mock_gear_args)

    mock_diff.assert_called_once()
    mock_qc.assert_called_once()
