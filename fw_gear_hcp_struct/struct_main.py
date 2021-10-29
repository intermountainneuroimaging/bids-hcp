import logging
import os.path as op
import shutil
import subprocess as sp
import sys
from zipfile import ZipFile

from fw_gear_hcp_struct import (
    FreeSurfer,
    PostFreeSurfer,
    PostProcessing,
    PreFreeSurfer,
    hcpstruct_qc_mosaic,
    hcpstruct_qc_scenes,
    struct_utils,
)
from utils import gear_arg_utils, results, helper_funcs

log = logging.getLogger(__name__)


def run(gear_args):
    """
    Main sequence of structural processing with FreeSurfer. Generally, these methods
    should be run sequentially, but each stage has its own check for whether the user
    chose to include the stage.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    Returns:
        rc (int): return code
    """
    gear_args.common['scan_type'] = 'struct'
    rc = 0
    check_FS_install(gear_args)

    if "PreFreeSurfer" in gear_args.common["stages"]:
        rc = run_preFS(gear_args)
    ###########################################################################
    # Must do a list comprehension to check for exact match.
    if ("FreeSurfer" in gear_args.common["stages"].split()) and (rc == 0):
        rc = run_FS(gear_args)
    ###########################################################################
    if ("PostFreeSurfer" in gear_args.common["stages"]) and (rc == 0):
        if not "FreeSurfer" in gear_args.common["stages"].split():
            # Get the zipped results from a previous run to continue the analysis
            # without re-running FS.
            if "hcpstruct_zip" in gear_args.common.keys():
                (
                    hcp_struct_list,
                    hcp_struct_config,
                ) = gear_arg_utils.make_hcp_zip_available(gear_args)
            else:
                log.error(
                    f"hcpstruct_zip (in Inputs) must be specified when selecting PostFreeSurfer"
                    f"without running FreeSurfer at the same time."
                )
                gear_args.common["errors"].append(
                    {
                        "message": "Struct PostProcessing defining/unzipping HCPstruct_zip",
                        "exception": "hcpstruct_zip (in Inputs) must be specified when selecting PostFreeSurfer without running FreeSurfer at the same time.",
                    }
                )

        rc = run_postFS(gear_args)
        if (gear_args.fw_specific["gear_dry_run"] is False) and (rc == 0):
            run_struct_qc(gear_args)
    return rc


def check_FS_install(gear_args):
    """
    Check a couple of the absolute prerequisites for FreeSurfer to run: the package
    defined in the path and a core template directory that is linked during recon-all.
    """
    # Utilize FreeSurfer license from config or project metadata
    proc = sp.run(["which", "freesurfer"], stdout=sp.PIPE, env=gear_args.environ)
    if proc.stdout:
        log.info(f'FreeSurfer installed {proc.stdout.decode("utf-8")}')
    else:
        log.fatal(
            "A valid FreeSurfer license must be present to run."
            "Please check your configuration and try again."
        )
        sys.exit(1)
    # Make the FreeSurfer average templates available
    template_dir = op.join(
        gear_args.environ["FREESURFER_HOME"], "subjects", "fsaverage"
    )
    log.debug(f"Checking for fsaverage in {template_dir}")
    templates = sp.run(["ls", template_dir], stdout=sp.PIPE, env=gear_args.environ)
    if len(templates.stdout.decode("utf-8").split("\n")[0]) < 5:
        log.error(f"fsaverage templates missing. FS will fail without them.")
        sys.exit(1)

    # Set some hcp specific output parameters:
    (
        gear_args.common["output_config"],
        gear_args.common["output_config_filename"],
    ) = struct_utils.configs_to_export(gear_args)

    gear_args.common["output_zip_name"] = op.join(
        gear_args.dirs["output_dir"],
        "{}_hcpstruct.zip".format(gear_args.common["subject"]),
    )


def run_preFS(gear_args):
    """
    First stage in structural HCP analysis. Creates folder structure within the bids_dir,
    corresponding to the subject label (minus the 'sub-' str).
    """
    rc = 0
    try:
        log.debug("Setting PreFreeSurfer parameters.")
        PreFreeSurfer.set_params(gear_args)
    except Exception as e:
        rc = helper_funcs.report_failure(
            gear_args, e, "Build params for PreFreeSurfer", "fatal"
        )
    ###########################################################################

    if not gear_args.common["errors"]:
        # Run PreFreeSurferPipeline.sh from subprocess.run
        try:
            log.debug("Executing PreFreeSurfer command.")
            PreFreeSurfer.execute(gear_args)
        except Exception as e:
            rc = helper_funcs.report_failure(
                gear_args, e, "Executing PreFreeSurfer", "fatal"
            )
    return rc


def run_FS(gear_args):
    """
    Set up the command line arguments (params in set_params) for FreeSurfer to complete
    the structural analysis. This stage takes about 9 hours to run and is essential for the
    functional and diffusion stages to be able to register images properly.
    gear_args.common["errors"] collects any issues with set up from this step or PreFreeSurfer.
    If there are errors, FreeSurfer analysis will not be initiated.

    Returns:
        Each of the following should be produced, even upon errors during the FreeSurfer run, if
        the 'save-on-gear-error' box is checked during set up.
        hcpstruct_zip: zipped file populated to /flywheel/v0/output that contains the majority
            of the structural analysis.
        log files: also zipped and made available as output. output ("o") and error ("e") logs
            are automatically generated by FreeSurfer
    """
    rc = 0
    try:
        log.debug("Setting FS parameters.")
        FreeSurfer.set_params(gear_args)
    except Exception as e:
        rc = helper_funcs.report_failure(
            gear_args, e, "Build params for FreeSurfer", "fatal"
        )

    if not gear_args.common["errors"]:
        # Run FreeSurferPipeline.sh from subprocess.run
        try:
            FreeSurfer.execute(gear_args)
            # Make the hcp_struct_zip file available in an 'immutable' field
            gear_args.common["hcpstruct_zip"] = gear_args.common["output_zip_name"]
        except Exception as e:
            # Since this is such a time intensive step, keep the log of what
            # was accomplished for quicker debugging.
            shutil.copy(
                op.join(
                    gear_args.environ["SUBJECTS_DIR"],
                    gear_args.common["subject"],
                    "scripts",
                    "recon-all.log",
                ),
                op.join(gear_args.dirs["output_dir"], "recon-all.log"),
            )
            ZipFile(op.join(gear_args.dirs["output_dir"], "recon-all.log"))
            log.info("recon-all.log available on Output tab for this analysis.")
            # Follow the same log procedures as other stages.
            rc = helper_funcs.report_failure(
                gear_args, e, "Executing eFreeSurfer", "fatal"
            )
    return rc


def run_postFS(gear_args):
    """
    Runs the postFreeSurfer routine and converts the aseg stats tables into csv's for
    further use (PostProcessing.py), if no errors were detected in setting up or running
    PreFreeSurfer or FreeSurfer.
    This stage can be entered after the hcpstruct_zip file is created in run_FS or a
    previous complete structural analysis. If one only wants to run the postprocessing
    stats conversion, the user may select 'stats-only_struct' in the setup configuration.
    """
    rc = 0
    try:
        log.debug("Setting up PostFreeSurfer.")
        PostFreeSurfer.set_params(gear_args)
    except Exception as e:
        rc = helper_funcs.report_failure(
            gear_args, e, "Build params for PostFreeSurfer", "fatal"
        )

    # Run PostFreeSurferPipeline.sh from subprocess.run
    if not gear_args.common["errors"]:
        if gear_args.structural["stats_only"]:
            log.info("Skipping straight to compiling stats.")
        else:
            try:
                PostFreeSurfer.execute(gear_args)
            except Exception as e:
                rc = helper_funcs.report_failure(
                    gear_args, e, "Compiling PostFreeSurfer stats", "fatal"
                )

        ###########################################################################
        # Run PostProcessing for "safe_listed" files
        #  - "safe_listed" files being copied direclty to ./output/ rather than
        #    being compressed into the result zip file.
        try:
            PostProcessing.set_params(gear_args)
            if gear_args.fw_specific["gear_dry_run"] is False:
                PostProcessing.execute(gear_args)
        except Exception as e:
            rc = helper_funcs.report_failure(
                gear_args, e, "Executing PostFreeSurfer", "fatal"
            )
    return rc


def run_struct_qc(gear_args):
    """
    Sends parameters to shell scripts that generate quality control images.

    Returns:
        png files: subject-derived results are overlaid on template images.
    """
    try:
        hcpstruct_qc_scenes.set_params(gear_args)
        hcpstruct_qc_scenes.execute(gear_args)

        hcpstruct_qc_mosaic.set_params(gear_args)
        hcpstruct_qc_mosaic.execute(gear_args)
        # Clean-up and output prep
        results.cleanup(gear_args)
    except Exception as e:
        helper_funcs.report_failure(gear_args, e, "Structural QC")