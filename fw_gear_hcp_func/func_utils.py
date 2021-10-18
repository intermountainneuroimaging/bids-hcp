"""
This is a module with specific functions for the HCP Functional Pipeline
"""
import glob
import logging
import os
import os.path as op
import shutil
from collections import defaultdict

log = logging.getLogger(__name__)


def remove_intermediate_files(gear_args):
    """
    Delete extraneous files used for the diffusion processing
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    # Delete extraneous processing files
    for d in ["prevols", "postvols"]:
        try:
            shutil.rmtree(
                op.join(
                    gear_args.dirs["bids_dir"],
                    gear_args.common["subject"],
                    gear_args.functional["fmri_name"],
                    "OneStepResampling",
                    d,
                )
            )
        except FileNotFoundError:
            log.info(f"{d} did not exist.")

    del_niftis = glob.glob(
        op.join(
            gear_args.dirs["bids_dir"],
            gear_args.common["subject"],
            gear_args.functional["fmri_name"],
            "MotionMatrices",
            "*.nii.gz",
        )
    )

    try:
        for nifti in del_niftis:
            os.remove(nifti)
    except FileNotFoundError:
        log.info(f"{nifti} did not exist.")


def configs_to_export(gear_args):
    """
    Export HCP Functional Pipeline configuration into the subject directory for record of settings.
    These keys are not anticipated to be passed back to set_params, so underscores should not matter.
    Return the config and filename
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    Returns:
        hcpfunc_config (dict): analysis configurations saved to json for future reference
        hcpfunc_config_filename (filepath): final location of the config options file.
    """
    config = {}
    hcpfunc_config = {"config": config}
    for key in [
        "reg_name",
        "subject",
        "fmri_name",
        "bias_correction",
        "mctype",
        "dof",
    ]:
        if key in gear_args.functional.keys():
            config[key] = gear_args.functional[key]
        elif key in gear_args.common.keys():
            config[key] = gear_args.common[key]

    if gear_args.common["current_stage"] == "fMRISurface":
        try:
            config["final_mri_resolution"] = gear_args.functional["surf_params"][
                "fmrires"
            ]
            config["grayordinates_resolution"] = gear_args.functional["surf_params"][
                "grayordinatesres"
            ]
            config["low_res_mesh"] = gear_args.functional["surf_params"]["lowresmesh"]
            config["smoothing_fwhm"] = gear_args.functional["surf_params"][
                "smoothingFWHM"
            ]
        except KeyError as e:
            log.debug(
                "Error setting up parameters for functional analysis. "
                "Look into setups for Generic shell scripts"
            )
            log.exception(e)

    hcpfunc_config_filename = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"],
        "sub-"
        + "{}_{}_hcpfunc_config.json".format(
            gear_args.common["subject"], gear_args.functional["fmri_name"]
        ),
    )

    return hcpfunc_config, hcpfunc_config_filename
