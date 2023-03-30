#!/usr/bin/env python3
import logging
import os.path as op
import sys
from glob import glob

from fw_gear_hcp_func import (
    GenericfMRISurfaceProcessingPipeline,
    GenericfMRIVolumeProcessingPipeline,
    func_utils,
    hcpfunc_qc_mosaic,
)
from utils import helper_funcs, results

log = logging.getLogger(__name__)


def run(gear_args, bids_layout):
    """
    Set up and complete the fMRIVolume and/or fMRISurface stages of the HCP Pipeline.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    Returns:
        rc (int): return code
    """
    rc = 0
    # Add current stage to common for reporting
    gear_args.common["scan_type"] = "func"

    for i, fmri_name in enumerate(gear_args.functional["fmri_names"]):
        set_func_args_single_file(gear_args, fmri_name, i)

        rc = set_func_args_list(gear_args, bids_layout)
        if ("Volume" in gear_args.common["stages"]) and (rc == 0):
            log.debug("Building and running fMRI Volume pipeline.")
            rc = run_fmri_vol(gear_args)

        if ("Surface" in gear_args.common["stages"]) and (rc == 0):
            log.debug("Building and running fMRI Surface pipeline.")
            rc = run_fmri_surf(gear_args)

        # Generate HCP-Functional QC Images
        # QC script was written for specific type of DCMethod
        if rc == 0:
            run_func_qc(gear_args)

    # log.debug("Zipping functional outputs.")
    # # Clean-up and output prep
    # gear_args.common["output_config_filename"]='hcpfunc_config.json'  # patch for "combined" config zip inside cleanup
    # # results.cleanup(gear_args)   ## DONT ZIP HERE - WAIT UNTIL THE END AFTER ALL STAGES

    return rc


def run_fmri_vol(gear_args):
    """
    fMRIVolume stage setup and execution.
    """
    rc = 0
    try:
        # Build and validate from Volume Processing Pipeline
        GenericfMRIVolumeProcessingPipeline.set_params(gear_args)
    except Exception as e:
        rc = helper_funcs.report_failure(
            gear_args, e, "Build params for fMRI volume processing", "fatal"
        )
    if rc == 0:
        try:
            GenericfMRIVolumeProcessingPipeline.execute(gear_args)

        except Exception as e:
            rc = helper_funcs.report_failure(
                gear_args, e, "Executing fMRI volume processing", "fatal"
            )
    return rc


def run_fmri_surf(gear_args):
    rc = 0
    try:
        # Build and validate from Surface Processign Pipeline
        GenericfMRISurfaceProcessingPipeline.set_params(gear_args)
    except Exception as e:
        rc = helper_funcs.report_failure(
            gear_args, e, "Build params for fMRI surface processing", "fatal"
        )
    if rc == 0:
        # Execute fMRI Surface Pipeline
        try:
            GenericfMRISurfaceProcessingPipeline.execute(gear_args)

        except Exception as e:
            rc = helper_funcs.report_failure(
                gear_args, e, "Executing fMRI surface processing", "fatal"
            )
    return rc


def run_func_qc(gear_args):
    """
    Sends parameters to shell scripts that generate quality control images.

    Returns:
        png files: subject-derived results are overlaid on template images.
    """
    try:
        hcpfunc_qc_mosaic.set_params(gear_args)
        hcpfunc_qc_mosaic.execute(gear_args)
    except Exception as e:
        helper_funcs.report_failure(gear_args, e, "Functional QC (func_main.py)")


def set_func_args_single_file(gear_args, specific_scan_name, scan_number_in_list):
    """Set the pre-requisite information that will be used to build the shell commands for functional processing."""
    gear_args.functional["fmri_name"] = specific_scan_name
    gear_args.functional["fmri_timecourse"] = gear_args.functional["fmri_timecourse_all"][scan_number_in_list]
    gear_args.functional["fmri_scout"] = gear_args.functional["fmri_scouts_all"][scan_number_in_list]


def set_func_args_list(gear_args, bids_layout):
    # Add distortion correction information
    gear_args.functional.update(
        helper_funcs.set_dcmethods(gear_args, bids_layout, "functional")
    )
    if gear_args.functional["dcmethod"] == "NONE":
        log.critical(
            "Must use a distortion correction method for fMRI Volume Processing. "
            'Please find needed fmaps or request "LegacyStyleData" mode to be '
            "added to the gear."
        )
        return 1

    # Set save configurations
    (
        gear_args.common["output_config"],
        gear_args.common["output_config_filename"],
    ) = func_utils.configs_to_export(gear_args)
    return 0
