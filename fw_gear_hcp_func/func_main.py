#!/usr/bin/env python3
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
        error code
    """
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
        # Some hcp-func specific output parameters:
        gear_args.common["output_zip_name"] = op.join(
            gear_args.dirs["output_dir"],
            "{}_{}_hcpfunc.zip".format(
                gear_args.common["subject"], gear_args.functional["fmri_name"]
            ),
        )

        if "Volume" in gear_args.common["stages"]:
            log.debug("Building and running fMRI Volume pipeline.")
            run_fmri_vol(gear_args)

        if "Surface" in gear_args.common["stages"]:
            log.debug("Building and running fMRI Surface pipeline.")
            run_fmri_surf(gear_args)

        # Generate HCP-Functional QC Images
        if gear_args.fw_specific["gear_dry_run"] is False:
            run_func_qc(gear_args)
    return 0


def run_fmri_vol(gear_args):
    """
    fMRIVolume stage setup and execution.
    """

    try:
        # Build and validate from Volume Processing Pipeline
        GenericfMRIVolumeProcessingPipeline.set_params(gear_args)
    except Exception as e:
        log.exception(e)
        log.error("Failed to build parameters for the fMRI Volume Pipeline!")
        gear_args.common["errors"].append(
            {
                "message": "Setting fMRIVol params",
                "exception": "Failed to build parameters for the fMRI Volume Pipeline!",
            }
        )
    # Save configurations
    (
        gear_args.common["output_config"],
        gear_args.common["output_config_filename"],
    ) = func_utils.configs_to_export(gear_args)
    if not gear_args.common["errors"]:
        try:
            GenericfMRIVolumeProcessingPipeline.execute(gear_args)
        except Exception as e:
            if gear_args.fw_specific["gear_save_on_error"]:
                results.cleanup(gear_args)
            gear_args.common["errors"].append(
                {"message": "Executing fMRIVol", "exception": e}
            )
            log.exception(e)
            log.fatal("The fMRI Volume Pipeline Failed!")
            sys.exit(1)


def run_fmri_surf(gear_args):
    try:
        # Build and validate from Surface Processign Pipeline
        GenericfMRISurfaceProcessingPipeline.set_params(gear_args)
    except Exception as e:
        log.exception(e)
        log.fatal("Validating Parameters for the fMRI Surface Pipeline Failed!")
        gear_args.common["errors"].append(
            {"message": "Setting fMRISurf params", "exception": e}
        )
    # Save configurations
    (
        gear_args.functional["output_config"],
        gear_args.functional["output_config_filename"],
    ) = func_utils.configs_to_export(gear_args)
    if not gear_args.common["errors"]:
        # Execute fMRI Surface Pipeline
        try:
            GenericfMRISurfaceProcessingPipeline.execute(gear_args)
        except Exception as e:
            if gear_args.fw_specific["gear_save_on_error"]:
                results.cleanup(gear_args)
            gear_args.common["errors"].append(
                {"message": "Executing fMRISurf", "exception": e}
            )
            log.exception(e)
            log.fatal("The fMRI Surface Pipeline Failed!")
            sys.exit(1)


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
        log.exception(e)
        log.error("HCP Functional QC Images has failed!")
        if gear_args.fw_specific["gear_save_on_error"]:
            results.cleanup(gear_args)
        gear_args.common["errors"].append(
            {"message": "Func QC did not run properly", "exception": e}
        )
