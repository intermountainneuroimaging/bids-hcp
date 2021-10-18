"""
This is a module with specific functions for the HCP Functional Pipeline
"""
import os.path as op
import subprocess as sp


def get_freesurfer_version(gear_args):
    """
    This function returns the version of freesurfer used.
    This is need to determine which HCP/FreeSurfer.sh to run.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    environ = gear_args.environ
    command = ["freesurfer --version"]
    result = sp.Popen(
        command,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        universal_newlines=True,
        shell=True,
        env=environ,
    )
    stdout, _ = result.communicate()
    start = stdout.find("-v") + 2
    end = stdout.find("-", start)
    version = stdout[start:end]
    return version


def configs_to_export(gear_args):
    """
    Export HCP Functional Pipeline configuration into the subject directory
    Return the config and filename
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    config = {}
    hcpstruct_config = {"config": config}
    for key in [
        "reg_name",
        "subject",
        "grayordinates_resolution",
        "grayordinates_template",
        "high_res_mesh",
        "low_res_mesh",
    ]:
        if key in gear_args.structural.keys():
            config[key] = gear_args.structural[key]
        elif key in gear_args.common.keys():
            config[key] = gear_args.common[key]

    hcpstruct_config_filename = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"],
        "sub-" + "{}_hcpstruct_config.json".format(gear_args.common["subject"]),
    )

    return hcpstruct_config, hcpstruct_config_filename
