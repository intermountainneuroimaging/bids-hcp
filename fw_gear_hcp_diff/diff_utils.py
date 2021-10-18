"""
This is a module with specific functions for the HCP Diffusion pipeline
"""
import os
import os.path as op


def configs_to_export(gear_args):
    """
    Export HCP Diffusion Pipeline configuration into the Subject directory
    Return the config and filename
    """
    config = {}
    hcpdiff_config = {"config": config}
    for key in ["reg_name", "subject", "dwi_name"]:
        if key in gear_args.diffusion.keys():
            config[key] = gear_args.diffusion[key]
        elif key in gear_args.common.keys():
            config[key] = gear_args.common[key]

    hcpdiff_config_filename = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"],
        "sub-"
        + "{}_{}_hcpdiff_config.json".format(
            gear_args.common["subject"], gear_args.diffusion["dwi_name"]
        ),
    )

    return hcpdiff_config, hcpdiff_config_filename


def make_sym_link(src, dest):
    """
    Make a symbolic link, if 'src' exists.  Do nothing, otherwise.
    """
    if src:
        os.symlink(src, dest)
