"""
Builds, validates, and excecutes parameters for the HCP script
/opt/HCP-Pipelines/FreeSurfer/FreeSurferPipeline.sh
part of the hcp-struct gear
"""
import os.path as op
from collections import OrderedDict

from flywheel.GearToolkitContext.interfaces.command_line import build_command_list, exec_command


def build(context):
    config = context.config
    params = OrderedDict()
    params["subject"] = config["Subject"]
    # Location to Put FreeSurfer Subject's Folder
    params["subjectDIR"] = op.join(context.work_dir, config["Subject"], "T1w")
    # T1w FreeSurfer Input (Full Resolution)
    params["t1"] = op.join(
        context.work_dir, config["Subject"], "T1w", "T1w_acpc_dc_restore.nii.gz"
    )
    # T1w FreeSurfer Input (Full Resolution)
    params["t1brain"] = op.join(
        context.work_dir, config["Subject"], "T1w", "T1w_acpc_dc_restore_brain.nii.gz"
    )
    # T2w FreeSurfer Input (Full Resolution)
    params["t2"] = op.join(
        context.work_dir, config["Subject"], "T1w", "T2w_acpc_dc_restore.nii.gz"
    )
    # This useless parameter does is no longer ignored in HCP v4.0.1
    # In fact, it gives an error.
    # params['printcom'] = " "
    context.gear_dict["FS-params"] = params


def validate(context):
    params = context.gear_dict["FS-params"]
    # Make sure these exists where expected
    not_found = []
    for param in ["subjectDIR", "t1", "t1brain", "t2"]:
        if param not in params.keys():
            raise Exception("FreeSurfer Parameter Building Failed.")
        if not op.exists(params[param]):
            not_found.append(params[param])
    if (len(not_found) > 0) and (not context.gear_dict["dry-run"]):
        raise Exception("The following files where not found: " + ",".join(not_found))


def execute(context):
    environ = context.gear_dict["environ"]
    command = []
    command.extend(context.gear_dict["command_common"])
    # HCP v4.0.1 has FreeSurferPipeline scripts for both Freesurfer 5.3.0 and
    # Freesurfer 6.0.2
    # For FreeSurfer 5.3.0: FreeSurferPipeline-v5.3.0-HCP.sh
    # For FreeSurfer 6.0.1: FreeSurferPipeline.sh
    if context.gear_dict["FreeSurfer_Version"][0] == "6":
        FreeSurfer_command = "FreeSurferPipeline.sh"
    else:
        FreeSurfer_command = "FreeSurferPipeline-v5.3.0-HCP.sh"

    command.append(op.join(environ["HCPPIPEDIR"], "FreeSurfer", FreeSurfer_command))

    command = build_command_list(command, context.gear_dict["FS-params"])
    stdout_msg = (
        "FreeSurfer logs (stdout, stderr) will be available in the "
        + 'file "pipeline_logs.zip" upon completion.'
    )

    context.log.info("FreeSurfer command: \n")
    exec_command(context, command, stdout_msg=stdout_msg)
