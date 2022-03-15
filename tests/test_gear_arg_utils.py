"""Test utils.gear_arg_utils"""
import logging
from unittest import mock
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pytest

from utils import gear_arg_utils, set_gear_args

log = logging.getLogger(__name__)


def test_sort_gear_args(caplog):
    mock_dict = {
        "hcpstruct_zip": {"location": {"path": "here/you/go"}},
        "outside_struct": "shiny",
        "inside_func": "pretty",
        "curved_dwi": "neato",
        "gear_dry_run": False,
        "stages": "stage1,stage2",
    }
    caplog.set_level(logging.INFO)
    sifted_dict = gear_arg_utils.sort_gear_args(mock_dict)
    assert sifted_dict["func"]["inside"] == "pretty"
    assert len(sifted_dict.keys()) == 5
    assert "INFO" in caplog.text


@pytest.mark.parametrize(
    "mock_effect, mock_cc, mock_msg", [(Exception, 0, "Invalid"), ("", 1, "")]
)
def test_make_hcp_zip_available(
    mock_effect, mock_cc, mock_msg, mock_gear_args, common_gear_arg_mocks, caplog,
):
    """
    The first step in the functional method requires that the output of the structural
    stage be located and unzipped. This test looks for whether the appropriate unzipping
    methods are called.
    """
    mock_exists, _, mock_preproc, mock_unzip = common_gear_arg_mocks
    if mock_effect:
        mock_exists.side_effect = mock_effect
    else:
        mock_exists.return_value = None
    gear_arg_utils.make_hcp_zip_available(mock_gear_args)
    assert mock_preproc.call_count == 1
    assert mock_unzip.call_count == mock_cc
    if mock_msg:
        assert mock_msg in caplog.text


@pytest.mark.parametrize("mock_val", ["find", None])
def test_query_json_locates_property(mock_val, mocker):
    """Test that the method will parse a pretend BIDS json sidecar to return sought after value."""
    fake_list = ["/lovely/list/of/files/brain.nii.gz"]
    mocker.patch("utils.gear_arg_utils.json.load", return_value={"seek": mock_val})
    with patch("builtins.open", mock_open(read_data="data")):
        p = gear_arg_utils.query_json(fake_list, "seek")
    assert p == mock_val


def test_set_subject_can_set_subject(mock_gtk_context):
    """
    Subject begins as empty string. Setting the subject should result in a non-empty variable.
    """
    mock_get = mock.MagicMock()
    mock_get.parents = {"subject": "Elmo"}
    mock_gtk_context.client.get.return_value = mock_get
    subj = gear_arg_utils.set_subject(mock_gtk_context)
    assert subj


def test_set_subject_fatal_with_no_parents(mock_gtk_context, caplog):
    """If Subject is set, but there are no parent containers, then the gear should fail."""
    gear_arg_utils.set_subject(mock_gtk_context)
    assert "critical" in caplog.text.lower()


def test_set_subject_fatal_with_no_subj(mock_gtk_context, caplog):
    mock_gtk_context.config.update({"subject": ""})
    gear_arg_utils.set_subject(mock_gtk_context)
    assert "Cannot have a zero-length subject." in caplog.text


@pytest.mark.parametrize(
    "fn_dict, config_len, msg",
    [
        ({0: "a_config.json", 1: "b.nii", 2: "/whack/", 3: "z.py"}, 2, ""),
        ({0: "a.json", 1: "b.nii", 2: "/whack/", 3: "z.py"}, 0, "configuration"),
    ],
)
@patch(
    "utils.gear_arg_utils.json.loads", return_value={"first": "last", "last": "first"}
)
def test_process_hcp_zip(
    mock_loads, fn_dict, config_len, msg, mock_gtk_context, mocker, caplog
):
    """Test whether the method detects a list of zipped files or returns the error that there is an empty list."""

    mock_file_list = []
    for f in range(4):
        mocked_file = MagicMock()
        mocked_file.filename = fn_dict[f]
        mock_file_list.append(mocked_file)
    mock_ZipFile = mocker.patch("utils.gear_arg_utils.ZipFile")
    mock_ZipFile.return_value.filelist = mock_file_list

    zip_file_list, config = gear_arg_utils.process_hcp_zip("fake_zip_file.zip")
    mock_ZipFile.assert_called_once()
    assert len(zip_file_list) == 3
    if config_len > 0:
        assert len(config["config"].keys()) == config_len
    assert msg in caplog.text


def test_unzip_hcp_attempts_to_unzip(mocker, mock_gear_args, caplog):
    """Searches for HCP structural file and extracts, if the files doesn't already exist"""
    mock_ZipFile = mocker.patch("utils.gear_arg_utils.ZipFile")
    caplog.set_level(logging.DEBUG)
    with patch("utils.gear_arg_utils.op.join", return_value=""):
        gear_arg_utils.unzip_hcp(mock_gear_args, "zipper.zip")
    mock_ZipFile.assert_called_once()
    assert "Unzipped the struct" in caplog.text
