import json
import logging
import os.path as op
import re
from collections import defaultdict
from zipfile import ZipFile

from flywheel_gear_toolkit import GearToolkitContext

log = logging.getLogger(__name__)


def sort_gear_args(in_dict):
    """
    Convert dictionaries to a nested dictionary structure that will be referenced throughout
    the gear. Each modality is a key within the dictionary at the highest level, allowing
    subsets of the dictionary to be passed to functions. Common parameters are kept as
    keys at the main level for ease of access.
    Args:
        in_dict (dictionary): any dictionary of parameters for the gear. Can be inputs, configs, or
        single entry updates.
    Returns:
        sifted_dict (dictionary): sifted according to HCP-related logic. Use dict.update() to add
        this dictionary to pre-existing ones.
    """
    sifted_dict = {
        "struct": defaultdict(),
        "func": defaultdict(),
        "dwi": defaultdict(),
        "fw_param": defaultdict(),
        "common": defaultdict(),
    }
    for k, v in in_dict.items():
        last = "_" + k.split("_")[-1]
        if k.lower() == "hcpstruct_zip":
            sifted_dict["common"][k.lower()] = v["location"]["path"]
        elif "struct" in k.lower():
            sifted_dict["struct"][k.replace(last, "")] = v
        elif ("func" in k.lower()) or ("fmri" in k.lower()):
            sifted_dict["func"][k.replace(last, "")] = v
        elif any(d in k.lower() for d in ["diffusion", "diff", "dwi"]):
            sifted_dict["dwi"][k.replace(last, "")] = v
        elif k.startswith("gear_"):
            sifted_dict["fw_param"][k] = v
        else:
            if (k.lower() == "stages") and ("," in v):
                log.info("Stages were not space-separated. Fixing that.")
                if not isinstance(v, list) and isinstance(v, str):
                    v = v.split(",")
                v = " ".join([s for s in v])
            sifted_dict["common"][k.lower()] = v

    return sifted_dict


def make_hcp_zip_available(gear_args):
    """
    Both functional and diffusion stages depend on the output of the HCP structural analysis.
    The zipped output must be located and unzipped for the processing to continue.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    Returns:
        hcp_struct_list : list of files to exclude from output zipping at the current stage
        hcp_struct_config : information about how the structural analysis was completed
        (error_count increases, if the file is not located or cannot be unzipped. Any error_count
        greater than 0 causes the program to continue running to isolate setup issues, but does not
        allow the algorithms to execute actual analysis.)
    """
    try:
        hcp_struct_zip_filename = gear_args.common["hcpstruct_zip"]
        hcp_struct_list, hcp_struct_config = process_hcp_zip(hcp_struct_zip_filename)
        if not all(op.exists(f) for f in hcp_struct_list):
            unzip_hcp(gear_args, hcp_struct_zip_filename)
        else:
            log.debug(f'Did not unzip the structural files, because they already existed.')
        return hcp_struct_list, hcp_struct_config
    except Exception as e:
        log.exception(e)
        log.error("Invalid hcp-struct zip file.")
        gear_args.common["errors"].append("Utils - unzipping HCPstruct")


def process_hcp_zip(zip_filename: str):
    """
    process_hcp_zip uses hcp-zip output of previous hcp run to create
    a list of contents and the configuration dictionary of that hcp run.
    Retained for compatibility in the cases where struct is run separately
    from other stages.
    Args:
        zip_filename (string): Absolute path of the zip file to examine
    Raises:
        log.exception: If the configuration file (config.json) is not found.
    Returns:
        tuple: (zip_file_list, config), the list of files contained in the zip
            file and the configuration dictionary of a previous run.
    """

    # Grab the whole file list from an exported zip,
    # put it in a list to parse through. So these will be the files
    # that do not get compressed into the gear output.
    # While we are at it, grab the *_config.json and return the file list
    # and gear config.
    # raise an exception if zip file or struct config not found.
    zip_file_list = []
    config = {}
    zf = ZipFile(zip_filename, "r")
    for fl in zf.filelist:
        if not (fl.filename[-1] == "/"):  # not (fl.is_dir()):
            zip_file_list.append(fl.filename)
            # grab exported hcp config
            if "_config.json" in fl.filename and not "__" in fl.filename:
                json_str = zf.read(fl.filename).decode()
                config = json.loads(json_str)
                # Keep compatibility if loads returns dict, otherwise make
                # config into a dict.
                config = config[0] if isinstance(config, list) else config
                # This corrects for leaving the initial "config" key out
                # of previous gear versions without error
                if "config" not in config.keys():
                    config = {"config": config}

    if len(config) == 0:
        log.exception(
            "Could not find a configuration within the "
            + "exported zip-file, {}.".format(zip_filename)
        )

    return zip_file_list, config


def unzip_hcp(gear_args, zip_filename):
    """
    unzip_hcp unzips the contents of zipped gear output into the working
    directory.  All of the files extracted are tracked from the
    above process_hcp_zip.
    Args:
        gear_args: The gear context object
            containing the 'gear_dict' dictionary attribute with key/value,
            'dry-run': boolean to enact a dry run for debugging
        zip_filename (string): The file to be unzipped
    """
    hcp_struct_zip = ZipFile(zip_filename, "r")
    log.info("Unzipping hcp struct file, %s", zip_filename)
    if not gear_args.fw_specific["gear_dry_run"]:
        hcp_struct_zip.extractall(gear_args.dirs["bids_dir"])
        log.debug(f'Unzipped the structural file to {gear_args.dirs["bids_dir"]}')


def query_json(fp_list: list, field: str):
    """
    Downloading the BIDS directory structure includes the json sidecars. Those sidecars
    have information that HCP needs to set analysis parameters. This method queries the
    sidecar that corresponds to the input file that needs parameters reported to HCP.
    Args:
        fp_list: filepath(s) to the input file(s), likely only one (for HCP analysis)
        field: name of the dicom field that has the required parameter

    Returns:
        parameter (str, float, int): the value associated with the requested parameter for
        HCP analysis.
    """
    if not isinstance(fp_list, list):
        fp_list = [fp_list]
    for fp in fp_list:
        pth, f = op.split(fp)
        f, ext = op.splitext(f)
        if ext in [".gz"]:
            f, ext = op.splitext(f)
        json_file = op.join(pth, (f + ".json"))
        with open(json_file, "r") as src:
            params = json.load(src)
            try:
                parameter = params[field]
                return parameter
            except KeyError:
                log.error(f"Did not locate {field} value in {json}")
                return None


def set_subject(gtk_context):
    """
    Part of the original implementation of the HCP Gears, but may be extraneous.
    set_subject queries the subject from the current gear configuration
    or session container (SDK).
    Exits ensuring the value of the subject is valid or raises an Exception.
    Args:
        gtk_context (flywheel.gear_context.GearContext): The gear context object
            with gear configuration attribute that is interrogated.
    Raises:
        Exception: Zero-length subject
        Exception: If the current analysis container does not have a subject
            container as a parent.
    """

    subject = ""
    # Subject in the gear configuration overrides everything else
    if "subject" in gtk_context.config.keys():
        # Correct for non-friendly characters
        subject = re.sub("[^0-9a-zA-Z./]+", "_", gtk_context.config["subject"])
        if len(subject) == 0:
            log.fatal("Cannot have a zero-length subject.")
    else:
        # Assuming valid client
        fw = gtk_context.client
        # Get the analysis destination ID
        dest_id = gtk_context.destination["id"]
        # Assume that the destination object has "subject" as a parent
        # This will raise an exception otherwise
        dest = fw.get(dest_id)
        if "subject" in dest.parents:
            subj = fw.get(dest.parents["subject"])
            subject = subj.label
        else:
            log.fatal(
                "The current analysis container does not have a subject "
                + "container as a parent."
            )

    log.info("Using %s as Subject ID.", subject)
    return subject
