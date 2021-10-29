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
from zipfile import ZIP_DEFLATED, ZipFile

import jsonpickle

log = logging.getLogger(__name__)

# ################################################################################
# # Clean-up and prepare outputs


def save_config(gear_args):
    """
    save_config uses the 'output_config' and 'output_config_filename' encapsulated in
    gear_args.common to save selected values from the analysis configuration to the working
    directory of the gear (/flywheel/v0/work).

    Args:
        gear_args: Must contain each of the following attributes with keys/values.
        (Set by "configs_to_export" in each "*_utils.py".)
            'output_config': A configuration dictionary created for downstream
                gears in the HCP pipeline
            'output_config_filename': The absolute filepath to use for the above
    """
    config = gear_args.common["output_config"]
    config_filename = gear_args.common["output_config_filename"]
    with open(config_filename, "w") as f:
        json.dump(config, f, indent=4)


def preserve_safe_list_files(gear_args):
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

    if not gear_args.fw_specific["gear_dry_run"]:
        for fl in gear_args.common["safe_list"]:
            log.info("Copying file to output: %s", fl)
            shutil.copy(fl, gear_args.dirs["output_dir"])


def zip_output(gear_args):
    """
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
    if {gear_args.common["scan_type"]} == "func":
        output_zipname = op.join(
            gear_args.dirs["output_dir"],
            f"{gear_args.common['subject']}_{gear_args.functional['fmri_name']}_hcp{gear_args.common['scan_type']}.zip",
        )
    else:
        output_zipname = op.join(
            gear_args.dirs["output_dir"],
            f"{gear_args.common['subject']}_hcp{gear_args.common['scan_type']}.zip",
        )

    if "exclude_from_output" in gear_args.common.keys():
        exclude_from_output = gear_args.common["exclude_from_output"]
    else:
        exclude_from_output = []

    log.info("Zipping output file %s", output_zipname)
    if not gear_args.fw_specific["gear_dry_run"]:
        try:
            os.remove(output_zipname)
        except Exception as e:
            pass

        os.chdir(gear_args.dirs["bids_dir"])
        outzip = ZipFile(output_zipname, "w", ZIP_DEFLATED)
        for root, _, files in os.walk(gear_args.common["subject"]):
            for fl in files:
                fl_path = op.join(root, fl)
                # only if the file is not to be excluded from output
                if fl_path not in exclude_from_output:
                    outzip.write(fl_path)
        outzip.close()


def zip_pipeline_logs(gear_args):
    """
    zip_pipeline_logs Compresses files in
    '/flywheel/v0/work/bids/logs' to '/flywheel/v0/output/pipeline_logs.zip'

    Args:
        gear_args: A gear context object
            leveraged for the location of the "working" and "output"
            directories of the log files.
    """

    # zip pipeline logs
    if {gear_args.common["scan_type"]} == "func":
        log_zipname = op.join(
            gear_args.dirs["output_dir"],
            f"{gear_args.common['fmri_name']}_{gear_args.common['scan_type']}_pipeline_logs.zip",
        )
    else:
        log_zipname = op.join(
            gear_args.dirs["output_dir"],
            f"{gear_args.common['scan_type']}_pipeline_logs.zip",
        )
    log.info("Zipping pipeline logs to %s", log_zipname)

    try:
        os.remove(log_zipname)
    except Exception as e:
        pass

    os.chdir(gear_args.dirs["bids_dir"])
    logzipfile = ZipFile(log_zipname, "w", ZIP_DEFLATED)
    for root, _, files in os.walk("logs"):
        log.debug(f"Found logs in {root}")
        for fl in files:
            logzipfile.write(os.path.join(root, fl))


def export_metadata(gear_args):
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


def cleanup(gear_args):
    """
    cleanup is used to complete all of the functions in 'results' and offer a simple
    interface for the main script to do so.

    Args:
        gear_args: The gear context object
            containing the 'gear_dict' dictionary attribute with keys/values
            utilized in the called helper functions.
    """

    # Move all images to output directory
    png_files = glob.glob(op.join(gear_args.dirs["bids_dir"], "*.png "))
    for fl in png_files:
        shutil.copy(fl, gear_args.dirs["output_dir"] + "/")

    save_config(gear_args)
    zip_output(gear_args)
    zip_pipeline_logs(gear_args)
    preserve_safe_list_files(gear_args)
    export_metadata(gear_args)
    create_error_log(gear_args)
    # List final directory to log
    log.info("Final output directory listing: gear_args.dirs['output_dir']")
    os.chdir(gear_args.dirs["output_dir"])
    duResults = sp.Popen(
        "du -hs *", shell=True, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = duResults.communicate()
    log.info("\n %s", stdout)


def create_error_log(gear_args):
    """Create a log message summarizing the errors and a log of all the arguments used in the
    analysis.
    Args:
         gear_args: The gear context object
         containing the 'gear_dict' dictionary attribute with keys/values
         utilized in the called helper functions.
    """
    if len(gear_args.common["errors"]) > 0:
        log.info(
            f"Encountered {len(gear_args.common['errors'])} error(s) during set_params routines. Please check the logs and correct the issues before re-running."
        )
    if gear_args.common["errors"]:
        log.debug(f'Errors were:\n{gear_args.common["errors"]}')

    # log.info(
    #     "Logging gear_args as output. Please consult logs particularly to make\n"
    #     "sure that all necessary files were located and placed in the \n"
    #     "appropriate modality configurations."
    # )
    # with open(op.join(gear_args.dirs["output_dir"], "gear_arg.json"), "w") as fp:
    #     jsonpickle.encode(gear_args)