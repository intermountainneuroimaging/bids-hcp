#!/usr/bin/env python3
import logging
import os
import os.path as op

from fw_gear_hcp_diff import DiffPreprocPipeline, hcpdiff_qc_mosaic, diff_utils
from utils import results

log = logging.getLogger(__name__)


def run(context):
    """
    Set up and complete the Diffusion Processing stage in the HCP Pipeline.
    """
    # Get file list and configuration from hcp-struct zipfile
    try:
        hcp_struct_zip_filename = context.get_input_path("StructZip")
        hcp_struct_list, hcp_struct_config = gear_preliminaries.preprocess_hcp_zip(
            hcp_struct_zip_filename
        )
        context.gear_dict["exclude_from_output"] = hcp_struct_list
        context.gear_dict["hcp_struct_config"] = hcp_struct_config
    except Exception as e:
        log.exception(e)
        log.error("Invalid hcp-struct zip file.")
        os.sys.exit(1)

    ############################################################################
    # Build and Validate Parameters
    # Doing as much parameter checking before ANY computation.
    # Fail as fast as possible.

    try:
        # Build and validate from Volume Processing Pipeline
        DiffPreprocPipeline.build(context)
        DiffPreprocPipeline.validate(context)
    except Exception as e:
        log.exception(e)
        log.fatal(
            "Validating Parameters for the " "Diffusion Preprocessing Pipeline Failed!"
        )
        os.sys.exit(1)

    ###########################################################################
    # Unzip hcp-struct results
    try:
        gear_preliminaries.unzip_hcp(context, hcp_struct_zip_filename)
    except Exception as e:
        log.exception(e)
        log.fatal("Unzipping hcp-struct zipfile failed!")
        os.sys.exit(1)

    ############################################################################
    # Execute HCP Pipelines
    # Some hcp-func specific output parameters:
    (
        context.gear_dict["output_config"],
        context.gear_dict["output_config_filename"],
    ) = diff_utils.configs_to_export(context)

    context.gear_dict["output_zip_name"] = op.join(
        context.output_dir,
        "{}_{}_hcpdiff.zip".format(
            context.config["Subject"], context.config["DWIName"]
        ),
    )

    # context.gear_dict['remove_files'] = diff_utils.remove_intermediate_files
    ###########################################################################
    # Pipelines common commands
    # "QUEUE" is used differently in FSL 6.0... We don't use it here.
    # QUEUE = "-q"
    LogFileDirFull = op.join(context.work_dir, "logs")
    os.makedirs(LogFileDirFull, exist_ok=True)
    FSLSUBOPTIONS = "-l " + LogFileDirFull

    command_common = [
        op.join(context.gear_dict["environ"]["FSLDIR"], "bin", "fsl_sub"),
        FSLSUBOPTIONS,
    ]

    context.gear_dict["command_common"] = command_common

    # Execute Diffusion Processing Pipeline
    try:
        DiffPreprocPipeline.execute(context)
    except Exception as e:
        log.exception(e)
        log.fatal("The Diffusion Preprocessing Pipeline Failed!")
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        os.sys.exit(1)

    # Generate Diffusion QC Images
    try:
        hcpdiff_qc_mosaic.build(context)
        hcpdiff_qc_mosaic.execute(context)
    except Exception as e:
        log.exception(e)
        log.fatal("HCP Diffusion QC Images has failed!")
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        exit(1)

    ###########################################################################
    # Clean-up and output prep
    results.cleanup(context)

    os.sys.exit(0)
