"""
Builds, validates, and excecutes parameters for the HCP helper script
/tmp/scripts/hcpdiff_qc_mosaic.sh
part of the hcp-dwi gear
"""

import logging
import os.path as op
from collections import OrderedDict

from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

log = logging.getLogger(__name__)


def set_params(gear_args):
    """

    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    Returns:

    """
    params = OrderedDict()

    params["qc_scene_root"] = op.join(
        gear_args.dirs["bids_dir"], gear_args.common["subject"]
    )
    params["DWIName"] = gear_args.diffusion["dwi_name"]
    params["qc_image_root"] = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"]
        + "_"
        + gear_args.diffusion["dwi_name"]
        + ".hcpdiff_QC.",
    )
    gear_args.diffusion["qc_params"] = params


def execute(gear_args):
    """

    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    Returns:

    """
    command = [op.join(gear_args.dirs["script_dir"], "hcpdiff_qc_mosaic.sh")]

    command = build_command_list(
        command, gear_args.diffusion["qc_params"], include_keys=False
    )

    command.append(">")
    command.append(op.join(gear_args.dirs["bids_dir"], "logs", "diffusionqc.log"))

    stdout_msg = (
        "Pipeline logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )

    log.info("Diffusion QC Image Generation command: \n")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
