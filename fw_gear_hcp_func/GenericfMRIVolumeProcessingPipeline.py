"""
Builds, validates, and excecutes parameters for the HCP script 
/opt/HCP-Pipelines/fMRIVolume/GenericfMRIVolumeProcessingPipeline.sh
part of the hcp-func gear
NOTE: the `utils.gear_preliminaries` module is in the `hcp-base` code
"""
import logging
import os
import os.path as op
import re
from collections import OrderedDict

import nibabel
from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Sets up the fMRIVolume configuration. Note that the params
    dictionary keys match with HCP pipeline commandline options, so
    the names should be retained.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    gear_args.common["current_stage"] = "fMRIVolume"
    params = OrderedDict()

    # Initialize parameters.
    # Explicitly rename the scripted labels that do not follow gear_args' names
    params["fmritcs"] = gear_args.functional["fmri_timecourse"]

    # use "FLIRT" to run FLIRT-based mcflirt_acc.sh, or "MCFLIRT" to
    # run MCFLIRT-based mcflirt.sh
    params["mctype"] = "MCFLIRT"
    # Initialize "NONE"s
    none_params = [
        "echodiff",
        "echo_spacing",
        "dcmethod",
        "topupconfig",
        "fmap_general_electric",
        "fmap_mag",
        "fmap_phase",
        "fmri_scout",
        "SE_Phase_Neg",
        "SE_Phase_Pos",
        "bias_correction",
        "unwarp_dir",
        "gdcoeffs",
        "fmri_name",
    ]

    for p in none_params:
        # Translate names to be consistent with HCP specs
        k = "".join(p.split("_"))
        # Translate names to be consistent with gear_args
        p = p.lower()
        if p in gear_args.functional.keys():
            params[k] = gear_args.functional[p]
        elif p in gear_args.common.keys():
            params[k] = gear_args.common[p]
        else:
            params[k] = "NONE"

    params["path"] = gear_args.dirs["bids_dir"]
    # The subject may have three different ways to be set:
    # 1) UI 2) hcp-struct.json zip 3) container
    # this is set in utils/gear_preliminaries.py:set_subject.
    params["subject"] = gear_args.common["subject"]

    zooms = (
        nibabel.load(gear_args.functional["fmri_timecourse"]).get_header().get_zooms()
    )
    params["fmrires"] = str(int(min(zooms[:3])))
    # If the zooms are unreliable for some reason, the original code had the following line.
    #    params["fmrires"] = "2"
    params["dof"] = gear_args.functional["dof"]

    if "temporalfilter" in gear_args.functional.keys():
        params["temporalfilter"] = gear_args.functional["temporalfilter"]
    else:
        params["temporalfilter"] = 200  # HCP default

    if "gdcoeffs" in gear_args.common.keys():
        params["gdcoeffs"] = gear_args.common["gdcoeffs"]

    # params["printcom"] = " "

    gear_args.functional["vol_params"] = params

    # A Distortion Correction method is required for fMRI Volume Processing
    if params["dcmethod"].upper() == "NONE":
        log.error(
            'Distortion Correction must be either "TOPUP" or '
            + '"SiemensFieldMap" to proceed with fMRI Volume Processing.'
            + "Please provide valid Spin Echo Positive/Negative or "
            + "Siemens GRE Phase/Magnitude field maps."
        )
        gear_args.common["errors"].append(
            {
                "message": "Setting fMRIVol params",
                "exception": 'Distortion Correction must be either "TOPUP" or '
                + '"SiemensFieldMap" to proceed with fMRI Volume Processing.'
                + "Please provide valid Spin Echo Positive/Negative or "
                + "Siemens GRE Phase/Magnitude field maps.",
            }
        )

    # Ensure that SE-Based BiasCorrection is only used with TOPUP
    # Distortion Correction
    if (params["dcmethod"].upper() != "TOPUP") and (
        params["biascorrection"].lower() == "sebased"
    ):
        log.error(
            "SE-Based BiasCorrection only available when "
            + "providing Pos and Neg SpinEchoFieldMap scans"
        )
        gear_args.common["errors"].append(
            {
                "message": "fMRIVol Distortion Correction",
                "exception": "SE-Based BiasCorrection only available when "
                + "providing Pos and Neg SpinEchoFieldMap scans",
            }
        )

    # Ensure that Distortion correction has a configuration file.
    if (params["dcmethod"].upper() == "TOPUP") and not params["topupconfig"]:
        log.error("Must have TOPUP configuration file.")
        gear_args.common["errors"].append("fMRI Vol needs TOPUP config.")

    if (params["dcmethod"].upper() == "TOPUP") and not params["unwarpdir"]:
        log.error("unwarpdir undefined for TOPUP fMRI Distortion Correction")
    # For testing
    return params


def execute(gear_args):
    # We want to take care of delivering the directory structure right away
    # when we unzip the hcp-struct zip
    os.makedirs(
        op.join(gear_args.dirs["bids_dir"], gear_args.common["subject"]), exist_ok=True
    )

    # Start by building command to execute
    command = []
    command.extend(gear_args.processing["common_command"])
    command.append(gear_args.processing["fMRIVolume"])
    command = build_command_list(command, gear_args.functional["vol_params"])

    stdout_msg = (
        "Pipeline logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )
    if gear_args.fw_specific["gear_dry_run"]:
        log.info("GenericfMRIVolumeProcessingPipeline command: \n")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
