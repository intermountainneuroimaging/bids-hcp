#!/usr/bin/env python3
import logging
import os.path as op
import sys

from fw_gear_hcp_diff import DiffPreprocPipeline, diff_utils, hcpdiff_qc_mosaic
from utils import helper_funcs, results

log = logging.getLogger(__name__)


def run(gear_args):
    """
    Set up and complete the Diffusion Processing stage in the HCP Pipeline.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    # Get file list and configuration from hcp-struct zipfile
    helper_funcs.run_struct_zip_setup(gear_args)

    run_diffusion(gear_args)

    if (not gear_args.common["errors"]) and (not gear_args.fw_specific["gear_dry_run"]):
        run_diff_qc(gear_args)

    return 0


def run_diffusion(gear_args):
    """
    The heart of the analysis. The method sets some HCP diffusion specific output parameters and then tries to
    launch the analysis process.
    """
    try:
        # Build and validate from Volume Processing Pipeline
        DiffPreprocPipeline.set_params(gear_args)
    except Exception as e:
        gear_args.common["errors"].append(
            {"message": "Setting up Diffusion", "exception": e}
        )
        log.exception(e)
        log.fatal(
            "Validating Parameters for the Diffusion Preprocessing Pipeline Failed!"
        )
        sys.exit(1)

    # Reports some of the parameters that were just set.
    (
        gear_args.common["output_config"],
        gear_args.common["output_config_filename"],
    ) = diff_utils.configs_to_export(gear_args)

    gear_args.common["output_zip_name"] = op.join(
        gear_args.dirs["output_dir"],
        "{}_{}_hcpdiff.zip".format(
            gear_args.common["subject"], gear_args.diffusion["dwi_name"]
        ),
    )
    if not gear_args.common["errors"]:
        try:
            DiffPreprocPipeline.execute(gear_args)
        except Exception as e:
            gear_args.common["errors"].append(
                {"message": "Executing Diffusion", "exception": e}
            )
            log.exception(e)
            if gear_args.fw_specific["gear_save_on_error"]:
                results.cleanup(gear_args)
            log.fatal("The Diffusion Preprocessing Pipeline Failed!")
            sys.exit(1)


def run_diff_qc(gear_args):
    """
    Sends parameters to shell scripts that generate quality control images.

    Returns:
        png files: subject-derived results are overlaid on template images.
    """
    if gear_args.fw_specific["gear_dry_run"] is False:
        try:
            hcpdiff_qc_mosaic.set_params(gear_args)
            hcpdiff_qc_mosaic.execute(gear_args)
            # Clean-up and output prep
            results.cleanup(gear_args)
        except Exception as e:
            log.exception(e)
            log.error("HCP Diffusion QC Images has failed!")
            if gear_args.fw_specific["gear_save_on_error"]:
                results.cleanup(gear_args)
