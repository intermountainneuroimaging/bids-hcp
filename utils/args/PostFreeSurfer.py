"""
Builds, validates, and excecutes parameters for the HCP script 
/opt/HCP-Pipelines/PostFreeSurfer/PostFreeSurferPipeline.sh
part of the hcp-struct gear
"""
import os
import os.path as op
import subprocess as sp
from collections import OrderedDict

from .common import build_command_list, exec_command


def build(context):
    config = context.config
    environ = context.gear_dict["environ"]
    # Some options that may become user-specified in the future,
    # but use standard HCP values for now
    # Usually 2mm ("1.6" also available)
    config["GrayordinatesResolution"] = "2"
    # Usually 32k vertices ("59" = 1.6mm)
    config["LowResMesh"] = "32"
    # (or 170494_Greyordinates = 1.6mm)
    config["GrayordinatesTemplate"] = "91282_Greyordinates"
    # Basically always 164k vertices
    config["HighResMesh"] = "164"

    params = OrderedDict()
    params["path"] = context.work_dir
    params["subject"] = config["Subject"]
    # (Need to rename make surf.gii and add 32k)
    params["surfatlasdir"] = op.join(
        environ["HCPPIPEDIR_Templates"], "standard_mesh_atlases"
    )
    # (Need to copy these in)$GrayordinatesSpaceDIR
    params["grayordinatesdir"] = op.join(
        environ["HCPPIPEDIR_Templates"], config["GrayordinatesTemplate"]
    )
    params["grayordinatesres"] = config["GrayordinatesResolution"]
    params["hiresmesh"] = config["HighResMesh"]
    params["lowresmesh"] = config["LowResMesh"]
    params["subcortgraylabels"] = op.join(
        environ["HCPPIPEDIR_Config"], "FreeSurferSubcorticalLabelTableLut.txt"
    )
    params["freesurferlabels"] = op.join(
        environ["HCPPIPEDIR_Config"], "FreeSurferAllLut.txt"
    )
    params["refmyelinmaps"] = op.join(
        environ["HCPPIPEDIR_Templates"],
        "standard_mesh_atlases",
        "Conte69.MyelinMap_BC.164k_fs_LR.dscalar.nii",
    )
    # Needs Checking for being FS or MSMSulc otherwise Error.
    params["regname"] = config["RegName"]
    params["printcom"] = " "
    # Unaccounted for parameters:
    #  CorrectionSigma=`opts_GetOpt1 "--mcsigma" $@` DEFAULT: sqrt(200)
    #  InflateExtraScale=`opts_GetOpt1 "--inflatescale" $@`f DEFAULT: 1
    context.gear_dict["POST-params"] = params


def validate(context):
    params = context.gear_dict["POST-params"]
    if not (params["regname"] in ["FS", "MSMSulc"]):
        raise Exception('RegName must be "FS" or "MSMSulc"!')


def execute(context):
    environ = context.gear_dict["environ"]
    command = []
    command.extend(context.gear_dict["command_common"])
    command.append(
        op.join(environ["HCPPIPEDIR"], "PostFreeSurfer", "PostFreeSurferPipeline.sh")
    )
    command = build_command_list(command, context.gear_dict["POST-params"])

    stdout_msg = (
        "PostFreeSurfer logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )

    context.log.info("PostFreeSurfer command: \n")
    exec_command(context, command, stdout_msg=stdout_msg)
