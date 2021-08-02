#!/usr/bin/env python3
import sys

from flywheel_gear_toolkit import GearToolkitContext

from utils.bids import bids_file_locator
from fw_gear_hcp_struct import struct_main
from fw_gear_hcp_func import func_main
from fw_gear_hcp_diff import diff_main


def main(gtk_context):
    # Run all the BIDS-specific downloads and config settings
    new_config = bids_file_locator.bidsInput()
    new_config.gather_bids_files()
    # TODO figure out if the class new_config is sufficient to pass around the config.json modifications or if the final method in gather_bids_file() needs to be written to capture the "new input file"
    e_code = 0
    if 'struct' in new_config.gtk_context.config.get('stages'):
        e_code = struct_main.run(new_config)

    if 'func' in new_config.gtk_context.config.get('stages') and e_code == 0:
        #TODO run a check for structural stage output. Exit if missing.
        e_code = func_main.run(new_config)

    if 'diff' in new_config.gtk_config.config.get('stages') and e_code == 0:
        #TODO determine if there are pre-conditions for running diffusion.
        # Looks like diffusion has the same structural stage requirement as fMRI.
        e_code = diff_main.run(new_config)

    sys.exit(e_code)

if __name__ == "__main__":
    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gtk_context:
    # Initialize logging, set logging level based on `debug` configuration
    # key in gear config.
        gtk_context.init_logging()

    # Pass the gear context into main function defined above.
        main(gtk_context)




