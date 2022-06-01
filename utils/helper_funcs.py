import json
import logging
import os
import os.path as op
import re
import subprocess as sp
import sys
from glob import glob

import nibabel
from bids.layout import BIDSLayout
from flywheel_gear_toolkit import GearToolkitContext

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
        fieldmap_set = check_intended_for_fmaps(
            bids_layout, gear_args.dirs["bids_dir"], gear_args.structural["raw_t1s"][0]
        )
        # fieldmap_set = bids_layout.get_fieldmap(
        #    gear_args.structural["raw_t1s"][0], return_list=True
        # )
    elif modality == "functional":
        fieldmap_set = check_intended_for_fmaps(
            bids_layout,
            gear_args.dirs["bids_dir"],
            gear_args.functional["fmri_timecourse"],
        )
        # fieldmap_set = bids_layout.get_fieldmap(
        #    gear_args.functional["fmri_timecourse"], return_list=True
        # )
    else:
        log.error(f"Fieldmap method not defined for {modality}")

    if fieldmap_set:
        log.debug(
            f"Examining fieldmap set to determine distortion correction methods: {modality}"
        )
        newline = "\n"
        files = [list(f.values()) for f in fieldmap_set]
        log.info(
            f"Available fieldmaps are\n{newline.join(f for x in files for f in x if len(f) > 10)}"
        )
        updated_configs = {}
        fmap_types = set.intersection(*map(set, fieldmap_set))
        if "phasediff" in fmap_types:
            try:
                configs_to_update = siemens_fieldmaps(
                    fieldmap_set, bids_layout, gear_args
                )
                updated_configs.update(configs_to_update)
            except Exception as e:
                log.error(f"Trying to use phasediff encountered:\n{e}")
        elif len(fieldmap_set) % 2 == 0:
            # Not totally sure it should always point to the same config file, but this is the file lister
            # in the original GenericfMRIVolumeProcessingPipeline
            if "fieldmap" in fmap_types:
                log.warning(
                    "Looks like you are trying to use a PEPolar type distortion correction method.\n"
                    "HCP was not originally designed to use these scans, but we will attempt TOPUP."
                )
            fmap_type = check_fmap_types(fmap_types)
            try:
                updated_configs["topupconfig"] = op.join(
                    gear_args.environ["HCPPIPEDIR_Config"], "b02b0.cnf"
                )
                configs_to_update = functional_fieldmaps(
                    fieldmap_set, fmap_type, bids_layout
                )
                updated_configs.update(configs_to_update)
            except Exception as e:
                log.error(
                    f"Trying to examine {fmap_type} fieldmaps encountered error:\n{e}"
                )
        else:
            log.info(
                f"Possible danger\n"
                f"fieldmap_set for {modality} = {fieldmap_set}\n"
                f"Is these the correct number and type of fmaps for your distortion correction method?\n"
                f"Make sure both directions are listed in the IntendedFors, not just the matching direction."
            )
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
                log.debug(
                    f"BIDS Curation did not list magnitude files as being intended for the same scan(s) as the phasediff file.\n"
                    f"Attempting to locate the corresponding mag files."
                )
                fieldmap_set[0]["magnitude1"] = glob(op.join(pth, "*_magnitude1.nii*"))[
                    0
                ]
                fieldmap_set[0]["magnitude2"] = glob(op.join(pth, "*_magnitude2.nii*"))[
                    0
                ]
            except:
                log.error(
                    f"BIDS Curation was incorrect for magnitude images and this\n"
                    f"gear could not automatically correct the curation. Please\n"
                    f"revisit the curation and try to re-run the gear."
                )
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


def functional_fieldmaps(fieldmap_set, fmap_type, bids_layout):
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
        enc_dir = bids_layout.get_metadata(fieldmap[fmap_type])[
            "PhaseEncodingDirection"
        ]
        if "-" in enc_dir:
            se_phase_neg = fieldmap[fmap_type]
        else:
            se_phase_pos = fieldmap[fmap_type]

    se_unwarp_dir = bids_layout.get_metadata(fieldmap_set[0][fmap_type])[
        "PhaseEncodingDirection"
    ]
    if "EffectiveEchoSpacing" in bids_layout.get_metadata(fieldmap_set[0][fmap_type]):
        echo_spacing = bids_layout.get_metadata(fieldmap_set[0][fmap_type])[
            "EffectiveEchoSpacing"
        ]
    elif "TotalReadoutTime" in bids_layout.get_metadata(fieldmap_set[fmap_type][0]):
        # HCP Pipelines do not allow users to specify total readout time directly
        # Hence we need to reverse the calculations to provide echo spacing that would
        # result in the right total read out total read out time
        # see https://github.com/Washington-University/Pipelines/blob/master/global/scripts/TopupPreprocessingAll.sh#L202
        log.info(
            "Did not find EffectiveEchoSpacing, calculating it from TotalReadoutTime"
        )
        # TotalReadoutTime = EffectiveEchoSpacing * (len(PhaseEncodingDirection) - 1)
        total_readout_time = bids_layout.get_metadata(fieldmap_set[0][fmap_type])[
            "TotalReadoutTime"
        ]
        phase_len = nibabel.load(fieldmap_set[0][fmap_type]).shape[
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


def report_failure(gear_args, exception, stage, level="nonfatal"):
    """
    Simple, consistent reporting for errors at any stage
    Args:
        gear_args
        exception (Exception): the exception thrown at the stage, where the failure occurred
        stage (str): description of the processing point, where the failure occurred
        level (str): fatal will exit with code 1, nonfatal will continue execution.
    """
    gear_args.common["errors"].append({"stage": stage, "Exception": exception})
    log.info(stage)
    log.exception(exception)

    if gear_args.fw_specific["gear_save_on_error"]:
        results.cleanup(gear_args)
    if level == "fatal":
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
        fieldmap_set = []
        for jfile in jsons:
            with open(jfile, "r") as j:
                jdata = json.loads(j.read())
                if any(p for p in jdata["IntendedFor"] if op.basename(filepath) in p):
                    # The fmap_type (BIDS suffix) helps indicate which DC method should be automatically chosen.
                    # Locate the final entity of the BIDS name with the next command.
                    # The final entity for fmaps will be "epi",'phasediff','magnitude?', 'phase?', or 'fieldmap'
                    jfile_fmap_type = jfile.split("_")[-1].split(".")[0]
                    # Find the NIfTI that corresponds to the json
                    jfile = glob(op.splitext(jfile)[0] + ".nii*")[0]
                    fieldmap_set.append({jfile_fmap_type: jfile})
                else:
                    log.info(
                        f"Unable to match {op.basename(filepath)} to an intended for image."
                    )
    except Exception as e:
        log.exception(e)

    if not fieldmap_set or fieldmap_set[0] == {}:
        # Even though the structure had to be initialized, an empty set should
        # trigger the secondary check below and skip fieldmap processing later, if
        # there are legitimately no IntendedFors.
        log.info(
            f"Using BIDSLayout method, BECAUSE {filepath} did not return a match in the fmap jsons."
        )
        # "BACKUP" method
        fieldmap_set = bids_layout.get_fieldmap(filepath, return_list=True)
    return fieldmap_set


def set_gdcoeffs_file(gtk_context: GearToolkitContext):
    """Gradient coefficients are **optional** for the analysis. Find the specified file
    or file set on the project level."""
    fw = gtk_context.client
    project_id = fw.get_analysis(gtk_context.destination.get("id")).parents.project
    project = fw.get_project(project_id)
    proj_file = next((f for f in project.files if "coeff" in f.name), None)
    if gtk_context.get_input_path("gdcoeffs"):
        gdcoeffs = gtk_context.get_input_path("gdcoeffs")
    # Look for file in project metadata
    elif proj_file:
        dest = op.join(gtk_context.work_dir, "coeff.grad")
        project.download_file(proj_file.name, dest)
        gdcoeffs = dest
    else:
        log.exception(
            "Manufacturer gdcoeffs file is not specified for analysis.\n"
            "Gradient Nonlinearity Correction will be skipped.\n"
            "Please contact your MR physicist or manufacturer for the file."
        )
        gdcoeffs = "NONE"
    if re.search(gdcoeffs, " +"):
        gdcoeffs = sanitize_gdcoeff_name(gdcoeffs)

    log.info("Using gradient nonlinearity coefficents file: "+gdcoeffs)
    return gdcoeffs


def sanitize_gdcoeff_name(orig_gdcoeffs: os.PathLike):
    """Remove any spaces from filename, so that the commandline is not disrupted."""
    new_name = "_".join(orig_gdcoeffs.split(" "))
    # Change the name in the available files
    os.rename(orig_gdcoeffs, new_name)
    return new_name


def check_fmap_types(fmap_types):
    fmap_type = list(set(fmap_types))
    if len(fmap_type) > 1:
        log.critical(
            "Unsure what type of distortion correction method you are attempting.\n"
            "Please check your BIDS curation and make sure the fmaps are identified correctly."
        )
    else:
        # bids_layout expects a quoted str for the key
        return fmap_type[0]
