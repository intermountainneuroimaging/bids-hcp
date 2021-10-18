"""
Builds, validates, and excecutes parameters for the HCP helper script
/tmp/scripts/hcpstruct_qc_mosaic.sh
part of the hcp-struct gear
"""
import logging
import os.path as op
import subprocess as sp
from collections import OrderedDict

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Set the parameters for the structural pipeline QC.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    params = OrderedDict()

    params["qc_scene_root"] = op.join(
        gear_args.dirs["bids_dir"], gear_args.common["subject"]
    )

    if "pre_params" not in gear_args.structural.keys():
        from fw_gear_hcp_struct import PreFreeSurfer

        PreFreeSurfer.set_params(gear_args)
    params["T1wTemplateBrain"] = gear_args.structural["pre_params"]["t1templatebrain"]

    params["qc_image_root"] = op.join(
        gear_args.dirs["bids_dir"], gear_args.common["subject"] + ".hcpstruct_QC."
    )

    gear_args.structural["qc_mosaic_params"] = params


def execute(gear_args):
    """
    Create mosaic of QC images for structural pipeline outputs.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    """
    command = [op.join(gear_args.dirs["script_dir"], "hcpstruct_qc_mosaic.sh")]
    for key in gear_args.structural["qc_mosaic_params"].keys():
        command.append(gear_args.structural["qc_mosaic_params"][key])
    command.append(">>")
    command.append(op.join(gear_args.dirs["bids_dir"], "logs", "structuralqc.log"))
    log.info(f"HCP-Struct QC Mosaic command: \n{' '.join(command)}\n\n")
    if not gear_args.fw_specific["gear_dry_run"]:
        result = sp.Popen(
            command,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            universal_newlines=True,
            env=gear_args.environ,
        )
        stdout, stderr = result.communicate()
        log.info(result.returncode)
        log.info(stdout)

        if result.returncode != 0:
            log.exception(
                f'The command:\n{" ".join(command)}\nfailed. See log for debugging.'
            )
