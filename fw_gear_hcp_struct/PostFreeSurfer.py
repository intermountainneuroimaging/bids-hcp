import logging
from collections import OrderedDict
from glob import glob

from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Builds, validates, and executes parameters for the HCP script
    /opt/HCP-Pipelines/PostFreeSurfer/PostFreeSurferPipeline.sh
    part of the hcp-struct gear
    """
    # Some options that may become user-specified in the future,
    # but use standard HCP values for now
    gear_args.common["current_stage"] = "PostFreeSurfer"
    # Usually 2mm ("1.6" also available)
    gear_args.common["grayordinates_resolution"] = "2"
    # Usually 32k vertices ("59" = 1.6mm)
    gear_args.common["low_res_mesh"] = "32"
    # (or 170494_Greyordinates = 1.6mm)
    gear_args.common["grayordinates_template"] = "91282_Greyordinates"
    # Basically always 164k vertices
    gear_args.common["high_res_mesh"] = "164"

    params = OrderedDict()
    params["path"] = gear_args.dirs["bids_dir"]
    params["subject"] = gear_args.common["subject"]
    # (Need to rename make surf.gii and add 32k)
    params["surfatlasdir"] = gear_args.templates["surf_atlas_dir"]
    # (Need to copy these in) $GrayordinatesSpaceDIR
    params["grayordinatesdir"] = [
        x
        for x in glob(gear_args.templates["grayordinates_template"])
        if gear_args.common["grayordinates_template"] in x
    ][0]
    params["grayordinatesres"] = gear_args.common["grayordinates_resolution"]
    params["hiresmesh"] = gear_args.common["high_res_mesh"]
    params["lowresmesh"] = gear_args.common["low_res_mesh"]
    params["subcortgraylabels"] = gear_args.templates["subcort_gray_labels"]
    params["freesurferlabels"] = gear_args.templates["freesurfer_labels"]
    params["refmyelinmaps"] = gear_args.templates["ref_myelin_maps"]
    # Needs Checking for being FS or MSMSulc otherwise Error.
    params["regname"] = gear_args.common["reg_name"]
    if not (params["regname"] in ["FS", "MSMSulc"]):
        # Somewhat enforced by enum in manifest
        raise Exception('RegName must be "FS" or "MSMSulc"!')
    # printcom is causing gear failure. Omit unless/until fixed.
    # params["printcom"] = " "
    # Unaccounted for parameters:
    #  CorrectionSigma=`opts_GetOpt1 "--mcsigma" $@` DEFAULT: sqrt(200)
    #  InflateExtraScale=`opts_GetOpt1 "--inflatescale" $@`f DEFAULT: 1
    gear_args.structural["post_fs_params"] = params
    # For testing
    return params


def execute(gear_args):
    command = []
    command.extend(gear_args.processing["common_command"])
    command.append(gear_args.processing["PostFreeSurfer"])
    command = build_command_list(command, gear_args.structural["post_fs_params"])

    stdout_msg = (
        "PostFreeSurfer logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )

    if gear_args.fw_specific["gear_dry_run"]:
        log.info("PostFreeSurfer command:\n{command}")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
