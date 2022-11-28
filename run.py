#!/usr/bin/env python
import json
import logging
import os.path as op
import sys
import shutil
from pathlib import Path
import os
from flywheel_gear_toolkit import GearToolkitContext

from fw_gear_hcp_diff import diff_main
from fw_gear_hcp_func import func_main
from fw_gear_hcp_struct import struct_main
from utils import environment, gear_arg_utils, helper_funcs
from utils.bids import bids_file_locator
from utils.set_gear_args import GearArgs
from utils.singularity import run_in_tmp_dir
from flywheel_gear_toolkit.licenses.freesurfer import install_freesurfer_license
from utils import freesurfer_utils

log = logging.getLogger(__name__)

# FWV0 = "/flywheel/v0"
# os.chdir(FWV0)

def main(gtk_context):
    # Set up the templates, config options from the config_json, and other essentials
    log.info("Populating gear arguments")
    gear_args = GearArgs(gtk_context)

    # Run all the BIDS-specific downloads and config settings
    log.info("Locating BIDS structure.")
    bids_info = bids_file_locator.bidsInput(gtk_context)
    bids_info.find_bids_files(gear_args)

    if bids_info.error_count > 0:
        log.info(
            "Please carefully check the error messages to correct "
            "your dataset before retrying the gear."
        )
        sys.exit(1)
    else:
        e_code = 0
    # Structural analysis
    if any("surfer" in arg.lower() for arg in [gear_args.common["stages"]]):
        if not gear_args.structural["avgrdcmethod"] == "NONE":
            # Add distortion correction information
            gear_args.structural.update(
                helper_funcs.set_dcmethods(gear_args, bids_info.layout, "structural")
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
            e_code += func_main.run(gear_args, bids_info.layout)

        # Diffusion analysis
        if any(
            arg in ["dwi", "diffusion"]
            for arg in [x.lower() for x in gear_args.common["stages"].split(" ")]
        ) and (e_code == 0):
            e_code += diff_main.run(gear_args)

    if e_code >= 1:
        return_code = e_code
    else:
        return_code = 0

    # save metadata
    metadata = {
        "analysis": {"info": {"resources used": {}, }, },
    }

    lsResults = sp.Popen(
        "cd "+gtk_context.output_dir+"; ls *.csv", shell=True, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = lsResults.communicate()
    files = stdout.strip("\n").split("\n")

    for f in files:
        if Path(f).exists():
            stats_df = pd.read_csv(f)
            as_json = stats_df.drop(stats_df.columns[0], axis=1).to_dict(
                "records"
            )[0]
            name = ".".join("_".join(f.split("_")[1:]).split(".")[0:-1]).replace(".","_")
            metadata["analysis"]["info"][name] = as_json

    if len(metadata["analysis"]["info"]) > 0:
        with open(f"{gtk_context.output_dir}/.metadata.json", "w") as fff:
            json.dump(metadata, fff)
        log.info(f"Wrote {gtk_context.output_dir}/.metadata.json")
    else:
        log.info("No data available to save in .metadata.json.")
    log.debug(".metadata.json: %s", json.dumps(metadata, indent=4))

    return return_code

if __name__ == "__main__":

    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext(config_path='/flywheel/v0/config.json') as gtk_context:
        # os.environ["SINGULARITY_NAME"] = "TEST1"
        scratch_dir = run_in_tmp_dir(gtk_context.config["gear-writable-dir"])
    # Has to be instantiated twice here, since parent directories might have
    # changed
    with GearToolkitContext() as gtk_context:
        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gtk_context.init_logging()

        FWV0 = Path.cwd()
        log.info("Running gear in %s", FWV0)

        # Constants that do not need to be changed
        FREESURFER_LICENSE = str(FWV0 / "freesurfer/license.txt")
        # MAKE SURE FREESURFER LICENSE IS FOUND
        os.environ["FS_LICENSE"] = str(FWV0 / "freesurfer/license.txt")

        # Now install the license
        install_freesurfer_license(
            gtk_context,
            FREESURFER_LICENSE,
        )

        freesurfer_utils.setup_freesurfer_for_singularity(FWV0)

        # Pass the gear context into main function defined above.
        return_code = main(gtk_context)

    # clean up (might be necessary when running in a shared computing environment)
    if scratch_dir:
        log.debug("Removing scratch directory")
        for thing in scratch_dir.glob("*"):
            if thing.is_symlink():
                thing.unlink()  # don't remove anything links point to
                log.debug("unlinked %s", thing.name)
        shutil.rmtree(scratch_dir)
        log.debug("Removed %s", scratch_dir)

    sys.exit(return_code)
