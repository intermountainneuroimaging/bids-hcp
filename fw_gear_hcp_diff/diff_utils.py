"""
This is a module with specific functions for the HCP Diffusion pipeline
"""
import os
import os.path as op


def configs_to_export(context):
    """
    Export HCP Diffusion Pipeline configuration into the Subject directory
    Return the config and filename
    """
    config = {}
    hcpdiff_config = {"config": config}
    for key in ["RegName", "Subject", "DWIName"]:
        if key in context.config.keys():
            config[key] = context.config[key]

    hcpdiff_config_filename = op.join(
        context.work_dir,
        context.config["Subject"],
        "{}_{}_hcpfunc_config.json".format(
            context.config["Subject"], context.config["DWIName"]
        ),
    )

    return hcpdiff_config, hcpdiff_config_filename


def make_sym_link(src, dest):
    """
    Make a symbolic link, if 'src' exists.  Do nothing, otherwise.
    """
    if src:
        os.symlink(src, dest)
