from collections import defaultdict
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_gear_args(mocker):
    mocker.patch("utils.set_gear_args")
    args = MagicMock(
        autospec=True,
        common={
            "stages": "PreFreeSurfer FreeSurfer PostFreeSurfer fMRIVolume fMRISurface Diffusion",
            "subject": "George",
            "current_stage": "diffusion",
            "errors": [],
            "hcpstruct_zip": "zippity_do_da",
            "template_size": "1mm",
            "brain_size": 5,
            "reg_name": "FS",
            "high_res_mesh": "nice",
            "low_res_mesh": "economical",
            "safe_list": ["bananas"],
        },
        dirs={
            "output_dir": "be/curious",
            "bids_dir": "/fw/v0/work/bids",
            "scenes_dir": "/like/a/motion/picture",
            "script_dir": "written/for/reading",
        },
        diffusion={
            "dwi_name": "is_a_monkey",
            "qc_params": "params",
            "pos_data": "pretend data",
            "neg_data": "sad data",
            "PE_dir": "sideways",
            "diff_params": {"latte": "da"},
            "echo_spacing": 1,
            "dof": 3,
        },
        environ={
            "SUBJECTS_DIR": "/the/tree/of/course",
            "FREESURFER_HOME": "is not really here",
        },
        functional={
            "fmri_name": "eat_bananas",
            "fmri_names": ["climb_trees", "eat_bananas"],
            "fmri_timecourse_all": ["one/file/path", "two/file/path"],
            "fmri_scouts_all": ["one/scout", "two/scout"],
            "mctype": "MCFlirt",
            "qc_params": "params",
            "fmri_timecourse": "a_timecourse",
            "dof": 12,
            "vol_params": "whatever",
            "surf_params": "whatever_take2",
            "echo_spacing": 0.01,
        },
        fw_specific={"gear_dry_run": False, "gear_save_on_error": True},
        structural={
            "reg_name": "Hmm what shall we call this",
            "grayordinates_resolution": 19682,
            "raw_t1s": "need_transformation",
            "raw_t2s": "also_need_transformation",
            "pre_params": {"t1templatebrain": "was already set"},
            "qc_scene_params": {"qc_outputdir": "another/dir"},
            "qc_mosaic_params": {"a_param": "a_val"},
            "unwarp_dir": "up",
            "fs_params": "plenty, of, params",
            "post_fs_params": "plenty, more, params",
            "metadata": {"analysis": {"info": defaultdict()}},
        },
        templates={
            "surf_atlas_dir": "atlas_shrugged",
            "template2mmmask": "slight_stutter",
            "t1template1mm": "just_a_millimeter",
            "t1templatebrain1mm": "just_a_brain",
            "t2template1mm": "contrast",
            "t2templatebrain1mm": "contrast_brain",
            "templatemask1mm": "mask",
            "fnirt_config": "always_sounds_funny",
            "grayordinates_template": "fake/elephant/91282_Greyordinates/dir",
            "subcort_gray_labels": "are_gone",
            "ref_myelin_maps": "here",
            "freesurfer_labels": "goofy, weird",
        },
    )
    return args


@pytest.fixture
def common_mocks(mocker):
    """These functions are called from within fw_gear_hcp_{modality}. Not all the
    modalities have all the calls, thus, there are 'dummy' values that can be
    passed back to the test function."""

    def mock(modality):
        try:
            mock_run = mocker.patch(
                "fw_gear_hcp_" + modality + "." + modality + "_main.sp.run"
            )
        except ModuleNotFoundError:
            mock_run = "dummy"

        try:
            mock_exit = mocker.patch(
                "fw_gear_hcp_" + modality + "." + modality + "_main.sys.exit"
            )
        except ModuleNotFoundError:
            mock_exit = "dummy"

        try:
            mock_copy = mocker.patch(
                "fw_gear_hcp_" + modality + "." + modality + "_main.shutil.copy"
            )
        except ModuleNotFoundError:
            mock_copy = "dummy"
        try:
            mock_results = mocker.patch(
                "fw_gear_hcp_" + modality + "." + modality + "_main.results.cleanup"
            )
        except ModuleNotFoundError:
            mock_results = "dummy"
        try:
            mock_zip = mocker.patch(
                "fw_gear_hcp_" + modality + "." + modality + "_main.ZipFile"
            )
        except:
            mock_zip = "dummy"
        try:
            mock_export = mocker.patch(
                "fw_gear_hcp_"
                + modality
                + "."
                + modality
                + "_main."
                + modality
                + "_utils.configs_to_export",
                return_value=["fake_config", "fake_config_filename"],
            )
        except ModuleNotFoundError:
            mock_export = "dummy"

        return mock_run, mock_exit, mock_copy, mock_results, mock_zip, mock_export

    return mock


@pytest.fixture
def qc_mocks(mocker):
    def mock(modality):
        mock_results = mocker.patch(
            "fw_gear_hcp_" + modality + "." + modality + "_main.results.cleanup"
        )
        mock_exit = mocker.patch(
            "fw_gear_hcp_" + modality + "." + modality + "_main.sys.exit"
        )
        try:
            mock_scene = mocker.patch(
                "fw_gear_hcp_"
                + modality
                + "."
                + modality
                + "_main.hcp"
                + modality
                + "_qc_scenes"
            )
        except:
            mock_scene = "dummy"

        mock_mosaic = mocker.patch(
            "fw_gear_hcp_"
            + modality
            + "."
            + modality
            + "_main.hcp"
            + modality
            + "_qc_mosaic"
        )
        return mock_results, mock_exit, mock_scene, mock_mosaic

    return mock


@pytest.fixture
def mock_hierarchy(mocker):
    return mocker.patch(
        "utils.bids.bids_file_locator.run_level.get_analysis_run_level_and_hierarchy",
        autospec=True,
        hierarchy={
            "run_label": 1,
            "subject_label": "sub-001",
            "session_label": "ses-001",
            "run_level": "acquisition",
        },
        layout={},
    )


@pytest.fixture
def mock_gtk_context(mocker):
    mocker.patch("flywheel_gear_toolkit.GearToolkitContext")
    gtk = MagicMock(
        autospec=True,
        config={
            "reg_name": "MSMSulc",
            "template_size": "1mm",
            "unwarp_dir_struct": "z",
            "aseg_csv": True,
            "avgrdcmethod_struct": "SiemensFieldMap",
            "bias_correction_func": "NONE",
            "brain_size": 150,
            "debug": True,
            "dof_diff": 6,
            "dof_func": 6,
            "dwi_name": "diffusion",
            "gear_abort_on_bids_error": False,
            "gear_dry_run": True,
            "gear_run_bids_validation": False,
            "gear_save_on_error": True,
            "mctype_func": "MCFLIRT",
            "stages": "PreFreeSurfer FreeSurfer PostFreeSurfer fMRIVolume fMRISurface Diffusion",
        },
        destination={"id": "12345ABCDE"},
        inputs={
            "gdcoeffs": {
                "base": "file",
                "hierarchy": {"type": "project", "id": "6036aae5bc23e6856e6e8ab8"},
                "location": {
                    "name": "coeff.grad",
                    "path": "/flywheel/v0/input/gdcoeffs/coeff.grad",
                },
                "object": {
                    "info": {},
                    "tags": [],
                    "measurements": [],
                    "classification": {},
                    "size": 3159,
                },
            },
            "hcpstruct_zip": {
                "base": "file",
                "hierarchy": {"type": "analysis", "id": "61205379c7adf7ea569f24e5"},
                "location": {
                    "name": "001_hcpstruct.zip",
                    "path": "/flywheel/v0/input/hcpstruct_zip/001_hcpstruct.zip",
                },
                "object": {
                    "info": {},
                    "tags": [],
                    "measurements": [],
                },
            },
        },
        work_dir={"test/data"},
    )
    return gtk


@pytest.fixture
def common_gear_arg_mocks(mocker):
    mock_exists = mocker.patch("utils.gear_arg_utils.op.exists")
    mock_join = mocker.patch("utils.gear_arg_utils.op.join")
    mock_preproc = mocker.patch(
        "utils.gear_arg_utils.process_hcp_zip",
        return_value=[["fake", "return", "list"], {"config": "goes_here"}],
    )
    mock_unzip = mocker.patch("utils.gear_arg_utils.unzip_hcp")
    return mock_exists, mock_join, mock_preproc, mock_unzip
