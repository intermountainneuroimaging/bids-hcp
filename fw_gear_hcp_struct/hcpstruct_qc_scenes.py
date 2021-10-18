"""
Builds, validates, and executes parameters for the HCP helper script
/tmp/scripts/hcpstruct_qc_scenes.sh
part of the hcp-struct gear
"""
import logging
import os
import os.path as op
import subprocess as sp
from collections import OrderedDict

from flywheel_gear_toolkit.interfaces.command_line import build_command_list

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Set the parameters for surface depictions of the structural pipeline output.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    """
    SCENE_DIR = gear_args.dirs["scenes_dir"]
    params = OrderedDict()
    # The following params correspond with positional arguments in hcpstruct_qc_scenes.sh
    params["qc_scene_template"] = op.join(
        SCENE_DIR, "TEMPLATE.hcpstruct_QC.very_inflated.164k_fs_LR.scene"
    )
    params["qc_scene_file"] = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"],
        "MNINonLinear",
        gear_args.common["subject"] + ".hcpstruct_QC.164k_fs_LR.scene",
    )
    params["qc_subject"] = gear_args.common["subject"]
    # Must include the final "/" to parse filepaths correctly.
    params["qc_scene_root"] = (
        op.join(gear_args.dirs["bids_dir"], gear_args.common["subject"]) + "/"
    )

    params["qc_outputdir"] = gear_args.dirs["bids_dir"]

    params["qc_image_root"] = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"],
        "MNINonLinear",
        gear_args.common["subject"] + ".hcpstruct_QC." + "inflated_",
    )
    # qc image size
    params["qc_image_params"] = "1440 900"
    gear_args.structural["qc_scene_params"] = params


def execute(gear_args):
    """
    Create surface depictions of the structural pipeline output.

    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    """
    environ = gear_args.environ
    SCRIPT_DIR = gear_args.dirs["script_dir"]
    os.makedirs(gear_args.structural["qc_scene_params"]["qc_outputdir"], exist_ok=True)
    gear_args.structural["qc_scene_params"].pop("qc_outputdir")
    command = [op.join(SCRIPT_DIR, "hcpstruct_qc_scenes.sh")]
    command.extend(gear_args.structural["qc_scene_params"].values())
    # command.append('>')
    # command.append(op.join(gear_args.dirs['bids_dir'],'logs','structuralqc.log'))
    log.info(f"HCP-Struct QC Scenes command: \n{' '.join(command)}\n\n")
    if not gear_args.fw_specific["gear_dry_run"]:
        result = sp.Popen(
            command,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            universal_newlines=True,
            env=environ,
        )
        stdout, stderr = result.communicate()
        log.info(result.returncode)
        log.info(stdout)

        if result.returncode != 0:
            log.exception(
                f"The command:\n{' '.join(command)}\nfailed. See log for debugging."
            )
