import json
import os.path as op  # needed for .filename?
from collections import defaultdict
from zipfile import ZipFile


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
    sifted_dict = defaultdict()
    for k, v in in_dict:
        if "struct" in k.lower():
            sifted_dict["struct"][k] = v
        elif "func" in k.lower():
            sifted_dict["func"][k] = v
        elif "diff" in k.lower():
            sifted_dict["diff"][k] = v
        elif k.startswith("gear-"):
            sifted_dict["fw_param"][k] = v
        else:
            sifted_dict[k] = v

    return sifted_dict


def preprocess_hcp_zip(zip_filename):
    """
    preprocess_hcp_zip uses hcp-zip output of previous hcp run to create
    a list of contents and the configuration dictionary of that hcp run.
    Retained for compatibility in the cases where struct is run separately
    from other stages.
    Args:
        zip_filename (string): Absolute path of the zip file to examine
    Raises:
        Exception: If the configuration file (config.json) is not found.
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
    zf = ZipFile(zip_filename)
    for fl in zf.filelist:
        if not (fl.filename[-1] == "/"):  # not (fl.is_dir()):
            zip_file_list.append(fl.filename)
            # grab exported hcp config
            if "_config.json" in fl.filename:
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
        raise Exception(
            "Could not find a configuration within the "
            + "exported zip-file, {}.".format(zip_filename)
        )

    return zip_file_list, config
