#!/usr/bin/env python3
import logging
import os.path as op
import sys

from flywheel_gear_toolkit import GearToolkitContext

from fw_gear_hcp_diff import diff_main
from fw_gear_hcp_func import func_main
from fw_gear_hcp_struct import struct_main
from utils import environment, gear_arg_utils, helper_funcs
from utils.bids import bids_file_locator
from utils.set_gear_args import GearArgs

log = logging.getLogger(__name__)


def main(gtk_context: GearToolkitContext):
    # Set up the templates, config options from the config_json, and other essentials
    log.info("Populating gear arguments")
    gear_args = GearArgs(gtk_context)

    # Run all the BIDS-specific downloads and config settings
    log.info("Locating BIDS structure.")
    bids_info = bids_file_locator.bidsInput(gtk_context)
    bids_info.find_bids_files(gear_args)

    e_code = 0
    # Structural analysis
    if any("surfer" in arg.lower() for arg in [gear_args.common["stages"]]):
        if not gear_args.structural["avgrdcmethod"] == "NONE":
            # Add distortion correction information
            gear_args.structural.update(
                helper_funcs.dcmethods(gear_args, bids_info.layout, "structural")
            )
        e_code += struct_main.run(gear_args)
    elif not gear_args.fw_specific["gear_dry_run"]:
        # If the analysis has been done piecemeal, then the previous struct zip must be specified
        # It is not efficient to search for all previous analyses and choose one of the structural zips.
        # This issue is particularly relevant to multiple analyses with different parameters. Choosing
        # one basically blindly is not advisable for FlyWheel.

        # Structural stage ends with zipping file. If that stage is complete, either from prior processing
        # or from current run, there should be a zip file to grab.
        gear_arg_utils.process_hcp_zip(gear_args.common["hcpstruct_zip"])

    # hcpstruct_zip is available when FS runs or when starting with a structural zip
    # identified.
    if ("hcpstruct_zip" in gear_args.common.keys()) or gear_args.fw_specific[
        "gear_dry_run"
    ]:
        # Functional analysis
        if any("fmri" in arg.lower() for arg in [gear_args.common["stages"]]) and (
            e_code == 0
        ):
            e_code += func_main.run(gear_args, bids_info)

        # Diffusion analysis
        if any(
            arg in ["dwi", "diffusion"]
            for arg in [x.lower() for x in gear_args.common["stages"].split(" ")]
        ) and (e_code == 0):
            e_code += diff_main.run(gear_args)

    if e_code >= 1:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    # TODO add Singularity capability
    # Singularity help https://singularityhub.github.io/singularity-hpc/r/bids-hcppipelines/

    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gtk_context:
        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gtk_context.init_logging()
        # Copy the key to the proper location in Docker for all analyses.
        environment.set_freesurfer_license(gtk_context)
        # Pass the gear context into main function defined above.
        main(gtk_context)
