"""
This module encapsulates functionality that is used in preparing and saving the
output of a gear. Some reorganization may make it more "universal"
"""
import glob
import json
import logging
import os
import os.path as op
import shutil
import subprocess as sp
import typing as t
from zipfile import ZIP_DEFLATED, ZipFile

import jsonpickle
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)
import utils.filemapper as filemapper
import utils.zip_htmls as zip_htmls

log = logging.getLogger(__name__)


# ################################################################################
# # Clean-up and prepare outputs


def save_config(config, config_filename):
    """
    save_config uses the 'output_config' and 'output_config_filename' encapsulated in
    gear_args.common to save selected values from the analysis configuration to the working
    directory of the gear (/flywheel/v0/work).

    Args:
        gear_args (GearToolkitContext): context with extra fields; must contain each of the following attributes with keys/values.
        (Set by "configs_to_export" in each "*_utils.py".)
            'output_config': A configuration dictionary created for downstream
                gears in the HCP pipeline
            'output_config_filename': The absolute filepath to use for the above
    """
    with open(config_filename, "w") as f:
        json.dump(config, f, indent=4)


def preserve_safe_list_files(safe_list, output_dir, dry_run=False):
    """
    preserve_safe_list_files copies the files listed in the 'safe_list' gear_args.common key
    directly to the output directory.  These files are to be presented directly to
    the user as well as compressed into the output zipfile.

    Args:
        gear_args: contains 'common' attribute with keys/values,
            'safe_list': a list of working directory files to place directly in
                the output directory
            'dry-run': a boolean parameter indicating whether or not to perform
            this under a 'dry-run' scenario
    """

    if not dry_run:
        for fl in safe_list:
            log.info("Copying file to output: %s", fl)
            shutil.copy(fl, output_dir)


def zip_output(
        destid, subject, session, output_dir, bids_dir, exclusions, dry_run=False
):
    """
    UPDATE: first step is to re-format HCP directory structure to match flywheel zip convention
       (destination.id/HCPPipe/sub-SUBJECT/ses-SESSION/*)
    zip_output Compresses the complete output of the gear
    (in /flywheel/v0/workdir/<Subject>)
    and places it in the output directory to be catalogued by the application.
    Only compresses files if 'dry-run' is set to False.

    Args:
        gear_args: The gear context object
            containing the 'gear_dict' dictionary attribute with keys/values,
            'dry-run': Boolean key indicating whether to actually compress or not
            'output_zip_name': output zip file to host the output
            'exclude_from_output': files to exclude from the output
            (e.g. hcp-struct files)
    """

    output_zipname = op.join(output_dir, f"{subject}_hcp.zip", )

    if exclusions:
        exclude_from_output = exclusions
    else:
        exclude_from_output = []

    log.info("Zipping output file %s", output_zipname)
    if not dry_run:
        try:
            os.remove(output_zipname)
        except Exception as e:
            pass

        os.chdir(bids_dir)

        # duplicate files to be zipped into new directory - then zip
        newpath = os.path.join(bids_dir, destid, "HCPPipe", "sub-" + subject, "ses-" + session)
        os.makedirs(newpath, exist_ok=True)

        for root, _, files in os.walk(subject):
            os.makedirs(os.path.join(newpath, root), exist_ok=True)
            for fl in files:
                fl_path = op.join(root, fl)
                # only if the file is not to be excluded from output
                if fl_path not in exclude_from_output:
                    shutil.copy2(fl_path, os.path.join(newpath, fl_path))

        # remove extra subject directory (easier than doing it above)
        for filename in os.listdir(os.path.join(newpath, subject)):
            shutil.move(os.path.join(newpath, subject, filename), os.path.join(newpath, filename))
        os.rmdir(os.path.join(newpath, subject))

        # create bids-derivative naming scheme
        filemapper.main(os.path.join(bids_dir, destid), destid)


        # NEW method to zip working directory using 'zip --symlinks -r outzip.zip data/'
        cmd = "zip --symlinks -r " + output_zipname + " " + str(destid)
        filemapper.execute_shell(cmd, cwd=bids_dir)

        # finally remove temp directory
        shutil.rmtree(os.path.join(bids_dir, destid))


def zip_pipeline_logs(
        output_dir: os.PathLike,
        bids_dir: os.PathLike,
):
    """
    zip_pipeline_logs Compresses files in
    '/flywheel/v0/work/bids/logs' to '/flywheel/v0/output/pipeline_logs.zip'

    Args:
        scan_type
    """

    # zip pipeline logs
    log_zipname = op.join(output_dir, f"pipeline_logs.zip")
    log.info("Zipping pipeline logs to %s", log_zipname)

    # Remove pre-existing log zips with the same name
    try:
        os.remove(log_zipname)
    except Exception as e:
        pass

    os.chdir(bids_dir)
    logzipfile = ZipFile(log_zipname, "w", ZIP_DEFLATED)
    for root, _, files in os.walk("logs"):
        log.debug(f"Found logs in {root}")
        for fl in files:
            logzipfile.write(os.path.join(root, fl))


def export_metadata(gear_args: GearToolkitContext):
    """
    If metadata exists (in gear_dict) for this gear write to the
    application. The flywheel sdk is used to write the metadata to the
    destination/analysis object. Another manner to commit this information to the
    application database is to write the dictionary to a '.metadata' file in
    /flywheel/v0/output.

    Args:
        gear_args: The gear context object
            containing the 'gear_dict' dictionary attribute with keys/values,
            'metadata': key that was initialized in
            utils.args.PostProcessing.{build,set_metadata_from_csv}.  If the
            'analysis' subkey is not present, this is an indicator that
            PostProcessing was not executed.
    """
    if "surfer" in gear_args.common["current_stage"].lower():
        metadata = gear_args.structural
    elif "fmri" in gear_args.common["current_stage"].lower():
        metadata = gear_args.functional
    else:
        metadata = gear_args.diffusion
    # Write Metadata to Analysis Object
    if ("analysis" in metadata) and (len(metadata["analysis"]["info"]) > 0):
        try:
            with open(
                    op.join(gear_args.dirs["output_dir"], ".metadata.json"), "w"
            ) as fff:
                json.dump(metadata, fff)
            log.info(f"Wrote op.join(gear_args.dirs['output_dir'], '.metadata.json')")
        except TypeError as e:
            log.exception(e)
    else:
        log.info("No data available to save in .metadata.json.")


def cleanup(gear_args: GearToolkitContext, gtk_context: GearToolkitContext):
    """
    Execute a series of steps to store outputs on the proper containers.

    Args:
        gear_args: The gear context object
            containing the 'gear_dict' dictionary attribute with keys/values
            utilized in the called helper functions.
    """

    # Move all images to output directory
    png_files = glob.glob(op.join(gear_args.dirs["bids_dir"], "*.png "))
    for fl in png_files:
        dest = op.join(gear_args.dirs["output_dir"], op.basename(fl))
        shutil.copy(fl, dest)

    save_config(
        gear_args.common["output_config"], gear_args.common["output_config_filename"]
    )

    zip_output(
        gear_args.common["destid"],
        gear_args.common["subject"],
        gear_args.common["session"],
        gear_args.dirs["output_dir"],
        gear_args.dirs["bids_dir"],
        gear_args.common["exclude_from_output"],
        dry_run=gear_args.fw_specific["gear_dry_run"],
    )
    zip_pipeline_logs(
        gear_args.dirs["output_dir"],
        gear_args.dirs["bids_dir"],
    )
    preserve_safe_list_files(
        gear_args.common["safe_list"],
        gear_args.dirs["output_dir"],
        gear_args.fw_specific["gear_dry_run"],
    )

    # TODO move csv files to output directory (externalize from other code?)
    # export_metadata(gear_args) ## this is in final cleanup code

    create_error_log(gear_args.common["errors"])
    # List final directory to log
    log.info("Final output directory listing: gear_args.dirs['output_dir']")
    os.chdir(gear_args.dirs["output_dir"])
    duResults = sp.Popen(
        "du -hs *", shell=True, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = duResults.communicate()
    log.info("\n %s", stdout)


def create_error_log(errors):
    """Create a log message summarizing the errors and a log of all the arguments used in the
    analysis.
    Args:
         gear_args: The gear context object
         containing the 'gear_dict' dictionary attribute with keys/values
         utilized in the called helper functions.
    """
    if len(errors) > 0:
        log.info(
            f"Encountered {len(errors)} error(s) during set_params routines. Please check the logs and correct the issues before re-running."
        )
    if errors:
        log.debug(f"Errors were:\n{errors}")


def executivesummary(gear_args: GearToolkitContext):
    """
    Run DCAN Lab's executive summary on completed analysis pipeline, zip up for viewing....

    Args:
        gear_args: The gear context object
            containing the 'gear_dict' dictionary attribute with keys/values
            utilized in the called helper functions.
    """
    #### run executive report here  - needs to be broken into running shell script, then layout-only py script (workaround)
    command = []
    outpath=os.path.join(gear_args.dirs["bids_dir"],gear_args.common["subject"])
    command.append("/opt/dcan-tools/executivesummary/executivesummary_preproc.sh")
    params = {"o": outpath,
              "s": gear_args.common["subject"],
              "i": os.path.join(gear_args.dirs["bids_dir"], "sub-"+gear_args.common["subject"], "ses-"+gear_args.common["session"], "func")}
    command = build_command_list(command, params, include_keys=True)

    filemapper.execute_shell(" ".join(command), cwd=gear_args.dirs["bids_dir"])

    cmd = "mkdir -p files ; mv executivesummary files/ ; mv T1_pngs files/ ; mv t1_bs_scene.scene files/"
    filemapper.execute_shell(cmd, cwd=outpath)

    command = []
    command.append("python /opt/dcan-tools/executivesummary/ExecutiveSummary.py --layout-only")
    params = {"o": os.path.join(outpath,"files"),
              "p": gear_args.common["subject"],
              "i": os.path.join(gear_args.dirs["bids_dir"], "sub-" + gear_args.common["subject"],
                                "ses-" + gear_args.common["session"], "func")}
    command = build_command_list(command, params, include_keys=True)

    stdout_msg = ''

    if gear_args.fw_specific["gear_dry_run"]:
        log.info("executivesummary command:\n{command}")
    try:
        terminal = sp.Popen(
            " ".join(command),
            shell=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            universal_newlines=True,
            cwd=os.getcwd(),
            env=gear_args.environ,
        )
        stdout, stderr = terminal.communicate()
        log.debug("\n %s", stdout)
        log.debug("\n %s", stderr)

        returncode = 0

        # zip html output
        zip_htmls.zip_htmls(gear_args.dirs["output_dir"], gear_args.common["destid"], os.path.join(outpath,"files","executivesummary"))

        if "error" in stderr.lower() or returncode != 0:
            gear_args["errors"].append(
                {"message": "executive summary failed. Check log", "exception": stderr}
            )
    except Exception as e:
        if gear_args.config["dry_run"]:
            # Error thrown due to non-iterable stdout, stderr, returncode
            pass
        else:
            log.exception(e)
            log.fatal('Unable to run executive summary')
