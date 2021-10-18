"""
Builds, validates, and excecutes parameters for the HCP helper script 
/tmp/scripts/hcpfunc_qc_mosaic.sh
part of the hcp-func gear
"""
import logging
import os
import os.path as op
from collections import OrderedDict

from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

log = logging.getLogger(__name__)


def set_params(gear_args):
    params = OrderedDict()
    params["qc_scene_root"] = op.join(
        gear_args.dirs["bids_dir"], gear_args.common["subject"]
    )
    params["fMRIName"] = gear_args.functional["fmri_name"]
    # qc_image_root indicates where the images are going
    params["qc_image_root"] = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"]
        + "_{}.hcp_func_QC.".format(gear_args.functional["fmri_name"]),
    )
    gear_args.functional["qc_params"] = params


def execute(gear_args):
    SCRIPT_DIR = gear_args.dirs["script_dir"]
    command = [op.join(SCRIPT_DIR, "hcpfunc_qc_mosaic.sh")]

    command = build_command_list(
        command, gear_args.functional["qc_params"], include_keys=False
    )

    command.append(">")
    command.append(op.join(gear_args.dirs["bids_dir"], "logs", "functionalqc.log"))

    stdout_msg = (
        "Pipeline logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )

    log.info("Functional QC Image Generation command: \n")
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
        stdout_msg=stdout_msg,
    )
