"""
Builds, validates, and executes parameters for the HCP script
/opt/HCP-Pipelines/PreFreeSurfer/PreFreeSurferPipeline.sh
part of the hcp-struct gear
"""
import logging
import os
import os.path as op
import subprocess as sp
import sys
from collections import OrderedDict

from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)

from utils import gear_arg_utils

log = logging.getLogger(__name__)


def set_params(gear_args):
    """
    Collect options for the PreFreeSurfer command from manifest and acquisition files. Perform
    basic checks, so that only likely successful configurations will be submitted for full analysis.

    Params dictionary is the basis of the PreFreeSurfer command. The dictionary is basically
    unpacked in key:value pairs to build the bash command. Therefore, the keys in the params
    should reflect the specific option available at the commandline.
    """
    gear_args.processing["current_stage"] = "PreFreeSurfer"
    params = OrderedDict()

    # Determine if key input files are accessible.
    missing = []
    for req in ["t1", "t2"]:
        if not any(req in k for k in gear_args.structural.keys()):
            missing.append(req)
    if len(missing) > 0:
        gear_args.common["errors"].append(
            {
                "message": "Missing required structural files.",
                f"exception": "Missing: {missing}",
            }
        )
        log.fatal(
            f"Unable to locate {missing} files. Will not be able to carry out analysis."
        )
        sys.exit(1)

    params["path"] = gear_args.dirs["bids_dir"]
    params["subject"] = gear_args.common["subject"]
    if (
        isinstance(gear_args.structural["raw_t1s"], list)
        and len(gear_args.structural["raw_t1s"]) > 1
    ):
        log.info(
            f"Found more than one T1. Using the first. Please check this is the intended action."
        )
    if isinstance(gear_args.structural["raw_t1s"], list):
        params["t1"] = gear_args.structural["raw_t1s"][0]
        params["t2"] = gear_args.structural["raw_t2s"][0]
    else:
        params["t1"] = gear_args.structural["raw_t1s"]
        params["t2"] = gear_args.structural["raw_t2s"]

    # Pre-Fill certain parameters with "NONE"
    none_params = [
        "unwarp_dir",
        "fmap_mag",
        "fmap_phase",
        "fmap_general_electric",
        "SE_Phase_Neg",
        "SE_Phase_Pos",
        "se_echo_spacing",
        "se_unwarp_dir",
        "echodiff",
        "t1_sample_spacing",
        "t2_sample_spacing",
        "gdcoeffs",
        "avgrdcmethod",
        "topupconfig",
    ]
    # Comment from the original gear; implications unknown:
    # the parameter "--bfsigma" is not accounted for
    for p in none_params:
        # Translate names to be consistent with HCP specs
        k = "".join(p.split("_"))
        # Translate names to be consistent with gear_args
        p = p.lower()
        if p in gear_args.structural.keys():
            params[k] = gear_args.structural[p]
        elif p in gear_args.common.keys():
            params[k] = gear_args.common[p]
        else:
            params[k] = "NONE"

    # format dwell_time to 15 places. DwellTime is req'd by HCP
    dwell_time_t1 = gear_arg_utils.query_json(params["t1"], "DwellTime")
    if dwell_time_t1:
        params["t1samplespacing"] = format(dwell_time_t1, ".15f")
    dwell_time_t2 = gear_arg_utils.query_json(params["t2"], "DwellTime")
    if dwell_time_t2:
        params["t2samplespacing"] = format(dwell_time_t2, ".15f")
    if not dwell_time_t1 or not dwell_time_t2:
        # Make sure that the distortion correction method and other
        # params are inline with missing dwell time methods.
        params = check_avgdcmethod(params)

    res_spec_templates = [
        "t1template",
        "t1templatebrain",
        "t2template",
        "t2templatebrain",
        "templatemask",
    ]
    for rst in res_spec_templates:
        # Narrow down the possible, matching template keys
        possible = [x for x in gear_args.templates.keys() if rst in x]
        # Select the key that matches the name of the rst being populated and the resolution (determined by template_size)
        pick = [x for x in possible if gear_args.common["template_size"] in x]
        params[rst] = gear_args.templates[pick[0]]

    params["brain_size"] = gear_args.common["brain_size"]
    # Examining Brain Size
    if params["brain_size"] < 10:
        log.info("Human Brains have a diameter larger than 1 cm!")
        log.info("Setting to default of 150 mm!")
        params["brain_size"] = 150

    params["fnirtconfig"] = gear_args.templates["fnirt_config"]
    # 3D acquisitions, like MPRAGE don't have PE directions in the json sidecars.
    # This must be provided by the user.
    params["unwarpdir"] = gear_args.structural["unwarp_dir"]

    # Should have been populated to gear_args during the find_bids_files -> structural args
    # and then passed to params earlier in this method. If not, try again here.
    # This quantity is needed for distortion correction
    if "echodiff" in params.keys():
        if params["echodiff"] == 0:
            raise Exception(
                "EchoTime1 and EchoTime2 are the same \
                    (Please ensure Magnitude input is TE1)! Exiting."
            )
        elif params["echodiff"] == "NONE":
            log.warning("echodiff set at NONE.")
            params = check_avgdcmethod(params)
        elif float(params["echodiff"]) < 0.1:
            log.debug(
                "Issue in fsl_prepare_fieldmap with incorrect echodiffs or phase ranges [6.283 radians]."
            )
            log.warning(
                f"Expecting echodiff values between 0.1 and 10.0 milliseconds.\n"
                f'Encountered echodiff of {params["echodiff"]}.'
            )
    else:
        log.error("No EchoTime metadata found in FieldMap input file!")
        gear_args.common["errors"].append(
            "Structural echodiff/TE did not have EchoTime metadata."
        )

    if "gdcoeffs" in gear_args.common.keys():
        params["gdcoeffs"] = gear_args.common["gdcoeffs"]
    # Though printcom is listed in the HCP pipeline options, the whitespace ending of the commands
    # seemed to cause `hostname: Temporary resolution` issues throughout the package. Discarding for now.
    # params["printcom"] = " "
    gear_args.structural["pre_params"] = params
    # For testing
    return params


def check_avgdcmethod(params):
    """There are a couple of special cases to check, so that execution does not hang on
    incorrectly set parameters
    Args
        params (dict): structural parameters that have been populated by the config.json
                        or other presets.
    Returns
        params (dict): updated values
    """

    # If "DwellTime" is not found in T1w/T2w, skip
    # readout distortion correction
    if (params["t1samplespacing"] == "NONE") and (params["t2samplespacing"] == "NONE"):
        if params["avgrdcmethod"] != "NONE":
            log.warning(
                '"DwellTime" tag not found. '
                + "Proceeding without readout distortion correction!"
            )
            params["avgrdcmethod"] = "NONE"
    # If there is not an echodiff and are no fmap images, then distortion correction should also be NONE
    if (params["fmapmag"] == "NONE" and params["fmapphase"] == "NONE") or (
        params["avgrdcmethod"] == "GeneralElectricFieldMap"
        and params["fmapgeneralelectric"] == "NONE"
    ):
        log.warning(
            "avgrdcmethod was set to %s\nNo fmaps available. Setting to NONE.",
            params["avgrdcmethod"],
        )
        params["avgrdcmethod"] = "NONE"
    return params


def execute(gear_args):
    os.makedirs(
        op.join(gear_args.dirs["bids_dir"], gear_args.common["subject"]), exist_ok=True
    )
    command = []
    command.extend(gear_args.processing["common_command"])
    command.append(gear_args.processing["PreFreeSurfer"])
    command = build_command_list(command, gear_args.structural["pre_params"])

    stdout_msg = (
        "PreFreeSurfer logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )
    if gear_args.fw_specific["gear_dry_run"]:
        log.info("PreFreeSurfer command:\n{command}")
    try:
        stdout, stderr, returncode = exec_command(
            command,
            dry_run=gear_args.fw_specific["gear_dry_run"],
            environ=gear_args.environ,
            stdout_msg=stdout_msg,
        )
        if "error" in stderr.lower() or returncode != 0:
            gear_args.common["errors"].append(
                {"message": "PreFS failed. Check log", "exception": stderr}
            )
    except Exception as e:
        if gear_args.fw_specific["gear_dry_run"]:
            # Error thrown due to non-iterable stdout, stderr, returncode
            pass
        else:
            log.debug(
                f"Checking that fsl_prepare_fieldmap is accessible:\n"
                f'{sp.run(["ls", "-l", "/usr/share/fsl/bin/fsl_prepare_fieldmap"], env=gear_args.environ)}'
            )
            gear_args.common["errors"].append(
                {"message": "DCMethod issue in PreFS.", "exception": e}
            )
