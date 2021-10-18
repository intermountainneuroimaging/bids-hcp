import logging
import os.path as op
import subprocess as sp

import nibabel
from bids.layout import BIDSLayout

from utils import gear_arg_utils

log = logging.getLogger(__name__)


def run_struct_zip_setup(gear_args):
    """
    1) Locate and unzip HCP structural analysis output.
    2) Exclude the structural files from the zipped output of this processing stage.
    3) Gather the configuration used during the structural processing stage.
    """
    if (
        "hcpstruct_zip" in gear_args.common.keys()
        and not gear_args.fw_specific["gear_dry_run"]
    ):
        hcp_struct_list, hcp_struct_config = gear_arg_utils.make_hcp_zip_available(
            gear_args
        )
        gear_args.common["exclude_from_output"] = hcp_struct_list
        gear_args.common["hcp_struct_config"] = hcp_struct_config


def dcmethods(gear_args, bids_layout, modality):
    """
    The distortion correction methods require consistent specification of polarity
    directions. This method finds the directions specified in the json sidecar and
    translates the information to the HCP specification.
    Args:
        gear_args (GearArgs):
        bids_layout (pybids.layout.BIDSLayout): Information about the BIDS-compliant directory structure from pyBIDS
    Returns:
        updated_configs
    """
    updated_configs = {}

    if modality == "structural":
        fieldmap_set = bids_layout.get_fieldmap(
            gear_args.structural["raw_t1s"][0], return_list=True
        )
    elif modality == "functional":
        fieldmap_set = bids_layout.get_fieldmap(
            gear_args.functional["fmri_timecourse"], return_list=True
        )
    else:
        log.error(f"Fieldmap method not defined for {modality}")
    if fieldmap_set:
        log.debug(
            f"Examining fieldmap set to determine distortion correction methods: {modality}"
        )
        updated_configs = {}
        if fieldmap_set[0]["suffix"] == "phasediff":
            try:
                configs_to_update = structural_fieldmaps(
                    fieldmap_set, bids_layout, gear_args
                )
                updated_configs.update(configs_to_update)
            except Exception as e:
                log.error(f"Trying to use phasediff encountered:\n{e}")
        elif fieldmap_set[0]["suffix"] == "epi" and len(fieldmap_set) == 2:
            # Not totally sure it should always point to the same config file, but this is the file lister
            # in the original GenericfMRIVolumeProcessingPipeline
            try:
                updated_configs["topupconfig"] = op.join(
                    gear_args.environ["HCPPIPEDIR_Config"], "b02b0.cnf"
                )
                configs_to_update = functional_fieldmaps(
                    fieldmap_set, bids_layout, gear_args
                )
                updated_configs.update(configs_to_update)
            except Exception as e:
                log.error(f"Trying to examine epi fieldmaps encountered:\n{e}")
        else:
            log.debug(f"fieldmap_set suffix = {fieldmap_set[0]['suffix']}")
            updated_configs["avgrdcmethod"] = "NONE"
            updated_configs["dcmethod"] = "NONE"
    else:
        log.warning(
            f"Problem with processing the fieldmaps for {modality}.\nLikely that the intended for field is not properly set.\nPlease check and retry the analysis."
        )
    return updated_configs


def structural_fieldmaps(fieldmap_set, bids_layout, gear_args):
    """
    Submethod to dcmethods to determine the parameters for distortion correction
    for structural images primarily.
    Args:
        fieldmap_set (pybids.layout.BIDSlayout.get_fieldmap): object containing
        parameters and filepaths for fmap images
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    Returns:
        configs_to_update (dict): k,v pairs related to fmap configs that should be communicated
        to the HCP workflow
    """
    pth = op.dirname(fieldmap_set[0]["phasediff"])
    configs_to_update = {}
    if pth:
        # Create Siemens style Magnitude and Phase
        merged_file = op.join(pth, "magfile.nii.gz")

        sp.run(
            [
                "fslmerge",
                "-t",
                merged_file,
                fieldmap_set[0]["magnitude1"],
                fieldmap_set[0]["magnitude2"],
            ]
        )

        phasediff_metadata = bids_layout.get_metadata(fieldmap_set[0]["phasediff"])
        te_diff = (
            phasediff_metadata["EchoTime2"] - phasediff_metadata["EchoTime1"]
        ) * 1000.0

        # HCP expects TE in milliseconds
        configs_to_update = {
            "te_diff": te_diff,
            "fmap_mag": merged_file,
            "fmap_phase": fieldmap_set[0]["phasediff"],
            "echodiff": "%.6f" % te_diff,
            "avgrdcmethod": "SiemensFieldMap",  # Structural pipeline uses avgrdcmethod kw
            "dcmethod": "SiemensFieldMap",
        }
    else:
        log.error(
            f"SiemensFieldMap was selected for Distortion Correction, but there was a problem locating a phasediff map in {fieldmap_set[0]}"
        )
        gear_args.common["errors"].append(
            {
                "message": "In helper_funcs.py Distortion Correction",
                "exception": f"problem locating a phasediff map in {fieldmap_set[0]}",
            }
        )
    return configs_to_update


def functional_fieldmaps(fieldmap_set, bids_layout, gear_args):
    """
    Submethod to dcmethods to determine the parameters for distortion correction
    for structural images primarily.
    Args:
        fieldmap_set (pybids.layout.BIDSlayout.get_fieldmap): object containing
        parameters and filepaths for fmap images
        bids_layout (pybids.layout.BIDSlayout): contains extra metadata related to
        the fieldmap_set.
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

    Returns:
        configs_to_update (dict): k,v pairs related to fmap configs that should be communicated
    to the HCP workflow
    """
    se_phase_neg = None
    se_phase_pos = None
    # Takes care of both directions and runs the checks that were more complicated in the original gears.
    for fieldmap in fieldmap_set:
        enc_dir = bids_layout.get_metadata(fieldmap["epi"])["PhaseEncodingDirection"]
        if "-" in enc_dir:
            se_phase_neg = fieldmap["epi"]
        else:
            se_phase_pos = fieldmap["epi"]

    se_unwarp_dir = bids_layout.get_metadata(fieldmap_set[0]["epi"])[
        "PhaseEncodingDirection"
    ]
    if "EffectiveEchoSpacing" in bids_layout.get_metadata(fieldmap_set[0]["epi"]):
        echo_spacing = bids_layout.get_metadata(fieldmap_set[0]["epi"])[
            "EffectiveEchoSpacing"
        ]
    elif "TotalReadoutTime" in bids_layout.get_metadata(fieldmap_set["epi"][0]):
        # HCP Pipelines do not allow users to specify total readout time directly
        # Hence we need to reverse the calculations to provide echo spacing that would
        # result in the right total read out total read out time
        # see https://github.com/Washington-University/Pipelines/blob/master/global/scripts/TopupPreprocessingAll.sh#L202
        log.info(
            "Did not find EffectiveEchoSpacing, calculating it from TotalReadoutTime"
        )
        # TotalReadoutTime = EffectiveEchoSpacing * (len(PhaseEncodingDirection) - 1)
        total_readout_time = bids_layout.get_metadata(fieldmap_set[0]["epi"])[
            "TotalReadoutTime"
        ]
        phase_len = nibabel.load(fieldmap_set[0]["epi"]).shape[
            {"x": 0, "y": 1}[se_unwarp_dir]
        ]
        echo_spacing = total_readout_time / float(phase_len - 1)
    else:
        log.error(
            "EffectiveEchoSpacing or TotalReadoutTime not defined for the fieldmap intended for T1w image. Please fix your BIDS dataset."
        )
    configs_to_update = {
        "se_phase_neg": se_phase_neg,
        "se_phase_pos": se_phase_pos,
        "se_unwarp_dir": se_unwarp_dir,
        "echo_spacing": echo_spacing,
        "avgrdcmethod": "TOPUP",  # structural kw is avgrdcmethod
        "dcmethod": "TOPUP",  # functional kw is dcmethod
        "bias_correction": "SEBASED",
    }
    return configs_to_update
