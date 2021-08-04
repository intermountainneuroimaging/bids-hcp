#!/usr/bin/env python3
import sys

from flywheel_gear_toolkit import GearToolkitContext

from fw_gear_hcp_diff import diff_main
from fw_gear_hcp_func import func_main
from fw_gear_hcp_struct import struct_main
from utils.bids import bids_file_locator


def main(gtk_context):
    # Run all the BIDS-specific downloads and config settings
    setup = bids_file_locator.bidsInput()
    setup.gather_bids_files()
    gear_args = setup.gear_args
    e_code = 0
    if "struct" in gear_args("stages"):
        e_code = struct_main.run(setup)

    # Structural stage ends with zipping file. If that stage is complete, either from prior processing
    # or from current run, there should be a zip file to grab.
    setup.update_struct_zip()
    if "func" in setup.gtk_context.config.get("stages") and e_code == 0:
        # TODO run a check for structural stage output. Exit if missing.
        e_code = func_main.run(setup)

    if "diff" in setup.gtk_config.config.get("stages") and e_code == 0:
        # TODO determine if there are pre-conditions for running diffusion.
        # Looks like diffusion has the same structural stage requirement as fMRI.
        e_code = diff_main.run(setup)

    sys.exit(e_code)


if __name__ == "__main__":
    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gtk_context:
        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gtk_context.init_logging()

        # Pass the gear context into main function defined above.
        main(gtk_context)
