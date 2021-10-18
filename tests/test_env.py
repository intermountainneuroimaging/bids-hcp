"""Test utils.environment.py"""
import importlib
import logging
import os
from unittest import mock
from unittest.mock import MagicMock, mock_open, patch

import pytest

from utils import environment

# Necessary to set the FWV0 in the module
module_dir = os.path.dirname(os.path.dirname(environment.__file__))
os.chdir(os.path.join(module_dir, "tmp"))
importlib.reload(environment)


def test_get_and_log_env_returns_values():
    """Simply test that a gear_env.json exists and is not empty"""
    env = environment.get_and_log_environment()
    assert env
    assert len(env.items()) > 0


@pytest.mark.parametrize(
    "config_val, outcome",
    [
        ("", 1),
        ("FREESURFER_LICENSE", 1),
        ("FreeSurferLicense", 2),
    ],
)
def test_set_FS_license(config_val, outcome, mock_gtk_context, caplog):
    """Test whether the FreeSurfer license can be identified."""
    if "FREE" in config_val:
        mock_gtk_context.config[config_val] = "The_KEYS_to_the_kingdom"
    elif "Free" in config_val:
        mock_gtk_context.get_input_path.return_value = "The_camels_of_the_kingdom"
    else:
        mock_gtk_context.get_input_path.return_value = ""
    caplog.set_level(logging.DEBUG)
    with patch("builtins.open", mock_open(read_data="license_contents")) as open_sesame:
        environment.set_freesurfer_license(mock_gtk_context)
    assert open_sesame.call_count == outcome
