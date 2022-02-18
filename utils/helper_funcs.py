import json
import logging
import os.path as op
import subprocess as sp
import sys
from glob import glob

import nibabel
from bids.layout import BIDSLayout

from utils import gear_arg_utils, results

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


def set_dcmethods(gear_args, bids_layout, modality):
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
        fieldmap_set = check_intended_for_fmaps(bids_layout, gear_args.dirs['bids_dir'], gear_args.structural["raw_t1s"][0])
        #fieldmap_set = bids_layout.get_fieldmap(
        #    gear_args.structural["raw_t1s"][0], return_list=True
        #)
    elif modality == "functional":
        fieldmap_set = check_intended_for_fmaps(bids_layout, gear_args.dirs['bids_dir'], gear_args.functional["fmri_timecourse"])
        #fieldmap_set = bids_layout.get_fieldmap(
        #    gear_args.functional["fmri_timecourse"], return_list=True
        #)
    else:
        log.error(f"Fieldmap method not defined for {modality}")

    if fieldmap_set:
        log.debug(
            f"Examining fieldmap set to determine distortion correction methods: {modality}"
        )
        newline = "\n"
        files = [list(f.values()) for f in fieldmap_set]
        log.info(f'Available fieldmaps are\n{newline.join(f for x in files for f in x if len(f) > 10)}')
        updated_configs = {}
        suffixes = [s['suffix'] for s in fieldmap_set if 'suffix' in s]
        if "phasediff" in suffixes:
            try:
                configs_to_update = siemens_fieldmaps(
                    fieldmap_set, bids_layout, gear_args
                )
                updated_configs.update(configs_to_update)
            except Exception as e:
                log.error(f"Trying to use phasediff encountered:\n{e}")
        elif ('epi' in suffixes) and len(fieldmap_set) == 2:
            # Not totally sure it should always point to the same config file, but this is the file lister
            # in the original GenericfMRIVolumeProcessingPipeline
            try:
                updated_configs["topupconfig"] = op.join(
                    gear_args.environ["HCPPIPEDIR_Config"], "b02b0.cnf"
                )
                configs_to_update = functional_fieldmaps(
                    fieldmap_set, bids_layout
                )
                updated_configs.update(configs_to_update)
            except Exception as e:
                log.error(f"Trying to examine epi fieldmaps encountered:\n{e}")
        else:
            log.debug(f"fieldmap_set = {fieldmap_set}")
            updated_configs["avgrdcmethod"] = "NONE"
            updated_configs["dcmethod"] = "NONE"
    else:
        log.warning(
            f"Did not locate fieldmaps for {modality}.\nLikely that the intended for field is not properly set.\nPlease check and retry the analysis, if there should have been IntendedFors."
        )
    return updated_configs


def siemens_fieldmaps(fieldmap_set, bids_layout, gear_args):
    """
    Submethod to set_dcmethods to determine the parameters for distortion correction
    for structural images primarily. Generates a magnitude map and requires a phasediff map.
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
        if "magnitude1" not in fieldmap_set[0]:
            try:
                log.debug(f'BIDS Curation did not list magnitude files as being intended for the same scan(s) as the phasediff file.\n'
                          f'Attempting to locate the corresponding mag files.')
                fieldmap_set[0]["magnitude1"] = glob(op.join(pth, '*_magnitude1.nii*'))[0]
                fieldmap_set[0]["magnitude2"] = glob(op.join(pth, '*_magnitude2.nii*'))[0]
            except:
                log.error(f'BIDS Curation was incorrect for magnitude images and this\n'
                          f'gear could not automatically correct the curation. Please\n'
                          f'revisit the curation and try to re-run the gear.')
                sys.exit(1)
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


def functional_fieldmaps(fieldmap_set, bids_layout):
    """
    Submethod to set_dcmethods to determine the parameters for distortion correction
    for structural images primarily.
    Args:
        fieldmap_set (pybids.layout.BIDSlayout.get_fieldmap): object containing
        parameters and filepaths for fmap images
        bids_layout (pybids.layout.BIDSlayout): contains extra metadata related to
        the fieldmap_set.

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

def report_failure(gear_args, exception, stage, level='nonfatal'):
    """
    Simple, consistent reporting for errors at any stage
    Args:
        gear_args
        exception (Exception): the exception thrown at the stage, where the failure occurred
        stage (str): description of the processing point, where the failure occurred
        level (str): fatal will exit with code 1, nonfatal will continue execution.
    """
    gear_args.common['errors'].append({'stage': stage, 'Exception': exception})
    log.info(stage)
    log.exception(exception)

    if gear_args.fw_specific["gear_save_on_error"]:
        results.cleanup(gear_args)
    if level == 'fatal':
        return 1


# Keep, as it may be needed in the future, but is finding all the same fmaps as get_fieldmap
def check_intended_for_fmaps(bids_layout, bids_dir, filepath):
    """To override the `get_fieldmap` guesses at intended for fmaps, check
    the fmap jsons 'intended for's first. That will be more transparent to the users.
    Args:
        filepath (path): path for the scan of interest
    """
    try:
        # Sorting the jsons should make it so increasing the iterator when finding a phasediff
        # will only happen after the magnitude images are already accounted for.
        jsons = sorted(glob(op.join(bids_dir, "**", "fmap", "*.json"), recursive=True))
        fieldmap_set = [{}]
        ix = 0
        for jfile in jsons:
            with open(jfile, "r") as j:
                jdata = json.loads(j.read())
                if any(p in filepath for p in jdata["IntendedFor"]):
                    jfile_suffix = jfile.split("_")[-1].split(".")[0]
                    jfile = glob(op.splitext(jfile)[0] + '.nii*')[0]
                    try:
                        fieldmap_set[ix].update({jfile_suffix:jfile})
                    except IndexError:
                        fieldmap_set.append({jfile_suffix:jfile})

                    if jfile_suffix in ['phasediff', 'epi']:
                        fieldmap_set[ix].update({'suffix': jfile_suffix})
                        ix +=1
    except Exception as e:
        log.exception(e)

    if not fieldmap_set or fieldmap_set[0] == {}:
        # Even though the structure had to be initialized, an empty set should
        # trigger the secondary check below and skip fieldmap processing later, if
        # there are legitimately no IntendedFors.
        log.info(f"Using BIDSLayout method, as {filepath} did not return a match in the fmap jsons.")
        # "BACKUP" method
        fieldmap_set = bids_layout.get_fieldmap(filepath, return_list=True)
    return fieldmap_set
