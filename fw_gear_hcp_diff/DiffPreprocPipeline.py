"""
Builds, validates, and excecutes parameters for the HCP script
/opt/HCP-Pipelines/DiffusionPreprocessing/DiffPreprocPipeline.sh
"""

import logging
import os
import os.path as op
from collections import OrderedDict

from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

from fw_gear_hcp_diff.diff_utils import make_sym_link

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Gather and sort the options for the Diffusion stage of HCP pipeline. Much
    of the trickier file finding is handled in the bids_file_locator.find_dwis method.
    This method handles formatting the pos/neg data filenames and other options
    to configure the analysis.
    """
    gear_args.common["current_stage"] = "Diffusion"

    # no gradient correction unless we are provided with a .grad file
    GradientDistortionCoeffs = gear_args.common.get("gdcoeffs", "NONE")

    # Some options that may become user-specified in the future, but use standard HCP
    # values for now. Cutoff for considering a volume "b0", generally b<10, but for 7T
    # data they are b<70
    b0maxbval = "100"

    # If JAC resampling has been used in eddy, this value
    # determines what to do with the output file.
    # 2 - include in the output all volumes uncombined (i.e.
    #    output file of eddy)
    # 1 - include in the output and combine only volumes
    #    where both LR/RL (or AP/PA) pairs have been
    #    acquired
    # 0 - As 1, but also include uncombined single volumes
    # Defaults to 1
    ExtraEddyArgs = " "
    # This may later become a configuration option...as GPUs are integrated
    # into the Flywheel architecture.  A patch to the DiffPreprocPipeline.sh
    # is needed for this to function correctly.
    No_GPU = True

    params = OrderedDict()
    # prefix for the output directory; set to the level above the subject
    params["path"] = gear_args.dirs["bids_dir"]
    params["subject"] = gear_args.common["subject"]
    # Name for the diffusion output dircctory
    params["dwiname"] = gear_args.diffusion["dwi_name"]
    params["posData"] = "@".join(gear_args.diffusion["pos_data"])
    params["negData"] = "@".join(gear_args.diffusion["neg_data"])
    # NOT phase encoding direction as x,y,z, but 1 (LR/RL) or 2 (AP/PA)
    params["PEdir"] = gear_args.diffusion["PE_dir"]
    params["echospacing"] = gear_args.diffusion["echo_spacing"]
    params["gdcoeffs"] = GradientDistortionCoeffs
    params["dof"] = gear_args.diffusion["dof"]
    params["b0maxbval"] = b0maxbval
    if "combine_data_flag" in gear_args.diffusion.keys():
        params["combine-data-flag"] = gear_args.diffusion["combine_data_flag"]
    else:
        params["combine-data-flag"] = 1
    # May need to eliminate the ExtraEddyArgs, if encountering problem. Currently, hard-coded to ' '
    params["extra-eddy-arg"] = ExtraEddyArgs
    params["no-gpu"] = No_GPU

    # params["printcom"] = " "
    gear_args.diffusion["diff_params"] = params

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
    command.append(gear_args.processing["DiffusionPreprocessing"])
    command = build_command_list(command, gear_args.diffusion["diff_params"])

    stdout_msg = (
        "Pipeline logs (stdout, stderr) will be available "
        + 'in the file {gear_args.common["output_zip_name"]} upon completion.'
    )
    if gear_args.fw_specific["gear_dry_run"]:
        log.info(f"DiffusionProcessing command:\n")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
