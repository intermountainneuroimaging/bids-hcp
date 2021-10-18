"""
Builds, validates, and excecutes parameters for the HCP script 
/opt/HCP-Pipelines/fMRISurface/GenericfMRISurfaceProcessingPipeline.sh
part of the hcp-func gear
"""
import logging
import os.path as op
from collections import OrderedDict

import nibabel
from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Sets up the fMRISurface configuration. Note that the params
    dictionary keys match with HCP pipeline commandline options, so
    the names should be retained.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    gear_args.common["current_stage"] = "fMRISurface"
    params = OrderedDict()
    params["path"] = gear_args.dirs["bids_dir"]
    params["subject"] = gear_args.common["subject"]
    params["fmriname"] = gear_args.functional["fmri_name"]
    # low_res_mesh usually 32k vertices ("59" = 1.60mm)
    params["lowresmesh"] = "32"

    zooms = (
        nibabel.load(gear_args.functional["fmri_timecourse"]).get_header().get_zooms()
    )
    params["fmrires"] = str(int(min(zooms[:3])))
    # params["fmrires"] = "2" # ****config option?****** #generally "2", "1.60" possible
    # Smoothing during CIFTI surface and subcortical resampling
    params["smoothingFWHM"] = params["fmrires"]
    # grayordinates_resolution usually 2mm ("1.60" also available)
    params["grayordinatesres"] = "2"
    if "temporalfilter" in gear_args.functional.keys():
        params["temporalfilter"] = gear_args.functional["temporalfilter"]
    else:
        params["temporalfilter"] = 200  # HCP default

    # The func gear configuration overides the struct configuration
    # else use the struct configuration.
    if gear_args.common["reg_name"] != "Empty":
        params["RegName"] = gear_args.common["reg_name"]
    elif "reg_name" in gear_args.common["hcp_struct_config"]["config"].keys():
        params["RegName"] = gear_args.common["hcp_struct_config"]["config"]["reg_name"]
        gear_args.common["reg_name"] = params["RegName"]
    else:
        log.error('Could not set "RegName" with current configuration.')
        gear_args.common["errors"].append(
            {
                "message": "Setting fMRISurface params",
                "exception": 'Could not set "RegName" with current configuration.',
            }
        )

    # params["printcom"] = ""
    gear_args.functional["surf_params"] = params
    # For testing
    return params


def execute(gear_args):
    # Start by building command to execute
    command = []
    command.extend(gear_args.processing["common_command"])
    command.append(gear_args.processing["fMRISurface"])
    command = build_command_list(command, gear_args.functional["surf_params"])

    stdout_msg = (
        "Pipeline logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )
    if gear_args.fw_specific["gear_dry_run"]:
        log.info("fMRI Surface Processing command: \n")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
