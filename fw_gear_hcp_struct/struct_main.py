import os
import logging

from utils import results

from fw_gear_hcp_struct import PostProcessing, hcpstruct_qc_mosaic, FreeSurfer, PreFreeSurfer, hcpstruct_qc_scenes, \
    PostFreeSurfer, struct_utils

log = logging.getLogger(__name__)

def run(context):
    """
    Set up and complete the FreeSurfer stages in the HCP Pipeline.
    """
    # Original code from hcp-struct func_main.py
    # Preamble: take care of all gear-typical activities.
    context.gear_dict = {}
    # Initialize all hcp-gear variables.
    gear_preliminaries.initialize_gear(context)
    context.log_config()
    # Utilize FreeSurfer license from config or project metadata
    try:
        gear_preliminaries.set_freesurfer_license(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            "A valid FreeSurfer license must be present to run."
            "Please check your configuration and try again."
        )
        os.sys.exit(1)

    # Validate gear configuration against gear manifest
    try:
        gear_preliminaries.validate_config_against_manifest(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal("Please make the prescribed corrections and try again.")
        os.sys.exit(1)

    # Can I automate this? Do I want to?
    context.gear_dict["FreeSurfer_Version"] = struct_utils.get_freesurfer_version(
        context
    )

    ###########################################################################
    # Build and Validate parameters for all stages of the pipeline before
    # attempting to execute. Correct parameters or gracefully recover where
    # possible.
    ###########################################################################
    # Ensure the subject_id is set in a valid manner (api or config)
    try:
        gear_preliminaries.set_subject(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            "The Subject ID is not valid. Examine and try again.",
        )
        os.sys.exit(1)

    # Build and Validate Parameters for the PreFreeSurferPipeline.sh
    try:
        PreFreeSurfer.build(context)
        PreFreeSurfer.validate(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            "Validating Parameters for the PreFreeSurferPipeline Failed.",
        )
        os.sys.exit(1)

    ###########################################################################
    # Build and Validate Parameters for the FreeSurferPipeline.sh
    try:
        FreeSurfer.build(context)
        # These parameters need to be validated after the PreFS run
        # No user-submitted parameters to validate at this level
        # FreeSurfer.validate(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal("Validating Parameters for the FreeSurferPipeline Failed.")
        os.sys.exit(1)

    ###########################################################################
    # Build and Validate Parameters for the PostFreeSurferPipeline.sh
    try:
        PostFreeSurfer.build(context)
        PostFreeSurfer.validate(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            "Validating Parameters for the PostFreeSurferPipeline Failed!"
        )
        os.sys.exit(1)

    ###########################################################################
    # Some hcp-func specific output parameters:
    (
        context.gear_dict["output_config"],
        context.gear_dict["output_config_filename"],
    ) = struct_utils.configs_to_export(context)

    context.gear_dict["output_zip_name"] = op.join(
        context.output_dir, "{}_hcpstruct.zip".format(context.config["Subject"])
    )
    # Pipelines common commands
    # QUEUE works differently in FSL 6.0.1..we are not using it.
    QUEUE = "-q "
    LogFileDirFull = op.join(context.work_dir, "logs")
    os.makedirs(LogFileDirFull, exist_ok=True)
    FSLSUBOPTIONS = "-l " + LogFileDirFull
    environ = context.gear_dict["environ"]
    command_common = [op.join(environ["FSLDIR"], "bin", "fsl_sub"), FSLSUBOPTIONS]

    context.gear_dict["command_common"] = command_common

    ###########################################################################
    # Run PreFreeSurferPipeline.sh from subprocess.run
    try:
        PreFreeSurfer.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            "The PreFreeSurferPipeline Failed.",
        )
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Run FreeSurferPipeline.sh from subprocess.run
    try:
        FreeSurfer.validate(context)
        FreeSurfer.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal("The FreeSurferPipeline Failed.")
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Run PostFreeSurferPipeline.sh from subprocess.run
    try:
        PostFreeSurfer.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal("The PostFreeSurferPipeline Failed!")
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Run PostProcessing for "whitelisted" files
    #  - "whitelisted" files being copied direclty to ./output/ rather than
    #    being compressed into the result zip file.
    try:
        PostProcessing.build(context)
        PostProcessing.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal("The Post Processing Failed!")
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Generate HCPStructural QC Images
    try:
        hcpstruct_qc_scenes.build(context)
        hcpstruct_qc_scenes.execute(context)

        hcpstruct_qc_mosaic.build(context)
        hcpstruct_qc_mosaic.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal("HCP Structural QC Images has failed!")
        if context.config["gear-save-on-error"]:
            results.cleanup(context)
        exit(1)

    ###########################################################################
    # Clean-up and output prep
    results.cleanup(context)
    return os.sys.exit(0)
