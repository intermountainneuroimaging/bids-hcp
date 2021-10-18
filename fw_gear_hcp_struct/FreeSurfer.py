"""
Builds, validates, and excecutes parameters for the HCP script
/opt/HCP-Pipelines/FreeSurfer/FreeSurferPipeline.sh
part of the hcp-struct gear
"""
import logging
import os.path as op
import sys
from collections import OrderedDict

from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Continue the FreeSurfer processing steps based on the files generated in the BIDS directory
    by PreFreeSurfer. PreFreeSurfer produces a T1w, T2w, and MNINonLinear folder.
    FreeSurfer produces a lot of files inside the bids/{subject}/T1w/{subject} folder.
    Args:
        gear_args: Object containing relevant gear and analysis set up parameters.

    """
    gear_args.common["current_stage"] = "FreeSurfer"
    params = OrderedDict()
    params["subject"] = gear_args.common["subject"]
    # Location to Put FreeSurfer Subject's Folder
    gear_args.environ["SUBJECTS_DIR"] = op.join(
        gear_args.dirs["bids_dir"], gear_args.common["subject"], "T1w"
    )
    # To keep backwards compatibility, retain the next line
    # Do not change the hyphen
    params["subject-dir"] = gear_args.environ["SUBJECTS_DIR"]
    try:
        # T1w FreeSurfer Input (Full Resolution)
        params["t1"] = op.join(
            gear_args.dirs["bids_dir"],
            gear_args.common["subject"],
            "T1w",
            "T1w_acpc_dc_restore.nii.gz",
        )
        # T1w FreeSurfer Input (Full Resolution)
        params["t1brain"] = op.join(
            gear_args.dirs["bids_dir"],
            gear_args.common["subject"],
            "T1w",
            "T1w_acpc_dc_restore_brain.nii.gz",
        )
        # T2w FreeSurfer Input (Full Resolution)
        params["t2"] = op.join(
            gear_args.dirs["bids_dir"],
            gear_args.common["subject"],
            "T1w",
            "T2w_acpc_dc_restore.nii.gz",
        )
    except:
        log.fatal("FreeSurfer Parameter Building Failed.")
        sys.exit(1)

    # Original note:
    # This useless parameter is no longer ignored in HCP v4.0.1
    # In fact, it gives an error.
    # params['printcom'] = " "
    gear_args.structural["fs_params"] = params

    # Validation step
    not_found = []
    for param in ["subject-dir", "t1", "t1brain", "t2"]:
        if param not in params.keys():
            raise Exception("FreeSurfer Parameter Building Failed.")
        if not op.exists(params[param]):
            not_found.append(params[param])
    if (len(not_found) > 0) and (not gear_args.fw_specific["gear_dry_run"]):
        log.error("The following files were not found: " + ",".join(not_found))
        gear_args.common["errors"].append(
            {
                "message": "Setting Struct params",
                "exception": (
                    "The following files were not found: " + ",".join(not_found)
                ),
            }
        )
    else:
        log.info("Files are available to run FreeSurfer.")
    # For testing
    return params


def execute(gear_args):
    command = []
    command.extend(gear_args.processing["common_command"])
    command.append(gear_args.processing["FreeSurfer"])
    command = build_command_list(command, gear_args.structural["fs_params"])
    stdout_msg = (
        "FreeSurfer logs (stdout, stderr) will be available in the "
        + 'file "pipeline_logs.zip" upon completion.'
    )

    if gear_args.fw_specific["gear_dry_run"]:
        log.info("FreeSurfer command:\n{command}")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
