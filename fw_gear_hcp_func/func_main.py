#!/usr/bin/env python3
from glob import glob
import logging
import os.path as op
import sys

from fw_gear_hcp_func import (
    GenericfMRISurfaceProcessingPipeline,
    GenericfMRIVolumeProcessingPipeline,
    func_utils,
    hcpfunc_qc_mosaic,
)
from utils import helper_funcs, results

log = logging.getLogger(__name__)


def run(gear_args, bids_info):
    """
    Set up and complete the fMRIVolume and/or fMRISurface stages of the HCP Pipeline.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    Returns:
        rc (int): return code
    """
    rc = 0
    gear_args.common['scan_type'] = 'func'
    # Get file list and configuration from hcp-struct zipfile
    helper_funcs.run_struct_zip_setup(gear_args)

    for i, fmri_name in enumerate(gear_args.functional["fmri_names"]):
        gear_args.functional["fmri_name"] = fmri_name
        gear_args.functional["fmri_timecourse"] = gear_args.functional[
            "fmri_timecourse_all"
        ][i]
        gear_args.functional["fmri_scout"] = gear_args.functional["fmri_scouts_all"][i]
        # Add distortion correction information
        gear_args.functional.update(
            helper_funcs.dcmethods(gear_args, bids_info.layout, "functional")
        )
        # Save configurations
        (
            gear_args.common["output_config"],
            gear_args.common["output_config_filename"],
        ) = func_utils.configs_to_export(gear_args)

        if ("Volume" in gear_args.common["stages"]) and (rc == 0):
            log.debug("Building and running fMRI Volume pipeline.")
            rc = run_fmri_vol(gear_args)

        if ("Surface" in gear_args.common["stages"]) and (rc == 0):
            log.debug("Building and running fMRI Surface pipeline.")
            rc = run_fmri_surf(gear_args)

        # Generate HCP-Functional QC Images
        # QC script was written for specific type of DCMethod
        if (
#            gear_args.fw_specific["gear_dry_run"] is False
            (rc == 0)
        ):
            run_func_qc(gear_args)
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
    if not gear_args.common["errors"]:
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
        results.zip_output(gear_args)
        hcpfunc_qc_mosaic.set_params(gear_args)
        hcpfunc_qc_mosaic.execute(gear_args)
        log.debug('Zipping functional outputs.')
        # Clean-up and output prep
        results.cleanup(gear_args)
    except Exception as e:
        helper_funcs.report_failure(gear_args, e, "Functional QC")
