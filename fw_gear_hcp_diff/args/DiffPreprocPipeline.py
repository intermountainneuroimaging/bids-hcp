"""
Builds, validates, and excecutes parameters for the HCP script
/opt/HCP-Pipelines/DiffusionPreprocessing/DiffPreprocPipeline.sh
"""

import logging
import os
import os.path as op
from collections import OrderedDict

from tr import tr

from ..diff_utils import make_sym_link
from ..gear_preliminaries import create_sanitized_filepath
from .common import build_command_list, exec_command

log = logging.getLogger(__name__)


def build(context):
    config = context.config
    inputs = context._invocation["inputs"]

    # Default Config Settings
    # DwellTime for DWI volumes
    EffectiveEchoSpacing = "NONE"

    # no gradient correction unless we are provided with a .grad file
    if "GradientCoeff" in inputs.keys():
        GradientDistortionCoeffs = create_sanitized_filepath(
            context.get_input_path("GradientCoeff")
        )
    else:
        GradientDistortionCoeffs = "NONE"

    # Set PEdir variable based on Phase-Encoding directions
    PEdir = ""
    pedir_pos = None
    pedir_neg = None
    if ("DWIPositiveData" in inputs.keys()) and ("DWINegativeData" in inputs.keys()):
        info_pos = inputs["DWIPositiveData"]["object"]["info"]
        info_neg = inputs["DWINegativeData"]["object"]["info"]
        if ("PhaseEncodingDirection" in info_pos.keys()) and (
            "PhaseEncodingDirection" in info_neg.keys()
        ):
            pedir_pos = tr("ijk", "xyz", info_pos["PhaseEncodingDirection"])
            pedir_neg = tr("ijk", "xyz", info_neg["PhaseEncodingDirection"])
            if ((pedir_pos, pedir_neg) == ("x-", "x")) or (
                (pedir_pos, pedir_neg) == ("x", "x-")
            ):
                PEdir = 1
            elif ((pedir_pos, pedir_neg) == ("y-", "y")) or (
                (pedir_pos, pedir_neg) == ("y", "y-")
            ):
                PEdir = 2
    # Create the posData and negData lists
    # posData and negData are '@'-delimited lists of nifti files on the command
    # line. We will build them, validate them, and link
    posData = []
    negData = []

    # Even With the DWIPos/Neg data checking out, above,
    # I am going to loop through everything to be more compact
    # making a lists of the pos/neg data/bvec/bval to validate later
    test = {"data": {}, "PE": {}, "bvecs": {}, "bvals": {}}
    valid = {"data": {}, "PE": {}, "bvecs": {}, "bvals": {}}

    base_dir = op.join(context.work_dir, "tmp_input")
    for i in range(1, 11):
        # i=1 is a special case here
        # the list of Diffusion files follows the format of
        # DWIPositiveData, DWIPositiveData2, ...3, ....
        if i == 1:
            j = ""
        else:
            j = i
        # We only add to posData and negData if both are present
        # If only one is present, warn them in validate()
        if ("DWIPositiveData{}".format(j) in inputs.keys()) and (
            "DWINegativeData{}".format(j) in inputs.keys()
        ):
            # Save the filepaths for later:
            test["data"]["Pos"] = create_sanitized_filepath(
                context.get_input_path("DWIPositiveData{}".format(j))
            )
            test["data"]["Neg"] = create_sanitized_filepath(
                context.get_input_path("DWINegativeData{}".format(j))
            )

            # We know what we want the end result to be. We append to the list
            # and ensure that it is correct in validate()
            posData.append(op.join(base_dir, "Pos{}".format(i), "data.nii.gz"))
            negData.append(op.join(base_dir, "Neg{}".format(i), "data.nii.gz"))
            # Making the directories for these as we go
            os.makedirs(op.join(base_dir, "Pos{}".format(i)), exist_ok=True)
            os.makedirs(op.join(base_dir, "Neg{}".format(i)), exist_ok=True)

            # Grab the Phase Encoding
            info_pos = inputs["DWIPositiveData{}".format(j)]["object"]["info"]
            info_neg = inputs["DWINegativeData{}".format(j)]["object"]["info"]
            if ("PhaseEncodingDirection" in info_pos.keys()) and (
                "PhaseEncodingDirection" in info_neg.keys()
            ):
                test["PE"]["Pos"] = tr("ijk", "xyz", info_pos["PhaseEncodingDirection"])
                test["PE"]["Neg"] = tr("ijk", "xyz", info_neg["PhaseEncodingDirection"])
            else:
                test["PE"]["Pos"] = None
                test["PE"]["Neg"] = None

            # Grab each of the pos/neg bvec/bval files or make them None
            if "DWIPositiveBvec{}".format(j) in inputs.keys():
                test["bvecs"]["Pos"] = create_sanitized_filepath(
                    context.get_input_path("DWIPositiveBvec{}".format(j))
                )
            else:
                test["bvecs"]["Pos"] = None

            if "DWINegativeBvec{}".format(j) in inputs.keys():
                test["bvecs"]["Neg"] = create_sanitized_filepath(
                    context.get_input_path("DWINegativeBvec{}".format(j))
                )
            else:
                test["bvecs"]["Neg"] = None

            if "DWIPositiveBval{}".format(j) in inputs.keys():
                test["bvals"]["Pos"] = create_sanitized_filepath(
                    context.get_input_path("DWIPositiveBval{}".format(j))
                )
            else:
                test["bvals"]["Pos"] = None

            if "DWINegativeBval{}".format(j) in inputs.keys():
                test["bvals"]["Neg"] = create_sanitized_filepath(
                    context.get_input_path("DWINegativeBval{}".format(j))
                )
            else:
                test["bvals"]["Neg"] = None
            # Comparing Phase Encoding Direction of the first to the Phase
            # Encoding.
            # The redundancy (first cycle is the first one) helps reduce the
            # complexity of the code.
            if (pedir_pos, pedir_neg) == (test["PE"]["Pos"], test["PE"]["Neg"]):
                # making a lists of the pos/neg data/bvec/bval to validate
                for key in ["data", "PE", "bvecs", "bvals"]:
                    valid[key]["Pos"] = test[key]["Pos"]
                    valid[key]["Neg"] = test[key]["Neg"]
            # if the phases are reversed, flip the order of our data/vecs/vals
            elif (pedir_pos, pedir_neg) == (test["PE"]["Neg"], test["PE"]["Pos"]):
                # making a lists of the pos/neg data/bvec/bval to validate
                for key in ["data", "PE", "bvecs", "bvals"]:
                    valid[key]["Pos"] = test[key]["Neg"]
                    valid[key]["Neg"] = test[key]["Pos"]
            # If something is way different, fill them with 'None'
            else:
                for key in ["data", "PE", "bvecs", "bvals"]:
                    valid[key]["Pos"] = None
                    valid[key]["Neg"] = None

            for key in ["data", "bvecs", "bvals"]:
                if "data" == key:
                    ext = "nii.gz"
                else:
                    ext = key[:-1]
                for pol in ["Pos", "Neg"]:
                    make_sym_link(
                        valid[key][pol],
                        op.join(base_dir, "{}{}".format(pol, i), "data.{}".format(ext)),
                    )

    # Read necessary acquisition params from fMRI
    EffectiveEchoSpacing = ""
    if "DWIPositiveData" in inputs.keys():
        info = inputs["DWIPositiveData"]["object"]["info"]
        if "EffectiveEchoSpacing" in info.keys():
            EffectiveEchoSpacing = format(info["EffectiveEchoSpacing"] * 1000, ".15f")

    # Some options that may become user-specified in the future, but use standard HCP
    # values for now. Cutoff for considering a volume "b0", generally b<10, but for 7T
    # data they are b<70
    b0maxbval = "100"
    # Specified value is passed as the CombineDataFlag value for the
    # eddy_postproc.sh script.
    CombineDataFlag = "1"

    # If JAC resampling has been used in eddy, this value
    # determines what to do with the output file.
    # 2 - include in the output all volumes uncombined (i.e.
    #    output file of eddy)
    # 1 - include in the output and combine only volumes
    #    where both LR/RL (or AP/PA) pairs have been
    #    acquired
    # 0 - As 1, but also include uncombined single volumes
    # Defaults to 1
    ExtraEddyArgs = " "
    # This may later become a configuration option...as GPUs are integrated
    # into the Flywheel architecture.  A patch to the DiffPreprocPipeline.sh
    # is needed for this to function correctly.
    No_GPU = True

    config = context.config
    params = OrderedDict()
    params["path"] = context.work_dir
    params["subject"] = config["Subject"]
    params["dwiname"] = config["DWIName"]
    params["posData"] = "@".join(posData)
    params["negData"] = "@".join(negData)
    params["PEdir"] = PEdir
    params["echospacing"] = EffectiveEchoSpacing
    params["gdcoeffs"] = GradientDistortionCoeffs
    params["dof"] = config["AnatomyRegDOF"]
    params["b0maxbval"] = b0maxbval
    params["combine-data-flag"] = CombineDataFlag
    params["extra-eddy-arg"] = ExtraEddyArgs
    params["no-gpu"] = No_GPU

    params["printcom"] = " "
    context.gear_dict["Diff-params"] = params


def validate(context):
    """
    The flow of `build()` is reconstructed to test particular configuration
    and file settings against one another.
    Future improvements may entail collecting this structure in a datatype
    in `build()` and iterating through that datatype in `validate()`.
    """
    inputs = context._invocation["inputs"]
    if ("DWIPositiveData" in inputs.keys()) and ("DWINegativeData" in inputs.keys()):
        info_pos = inputs["DWIPositiveData"]["object"]["info"]
        info_neg = inputs["DWINegativeData"]["object"]["info"]
        if ("PhaseEncodingDirection" in info_pos.keys()) and (
            "PhaseEncodingDirection" in info_neg.keys()
        ):
            pedir_pos = inputs["DWIPositiveData"]["object"]["info"][
                "PhaseEncodingDirection"
            ]
            pedir_neg = inputs["DWINegativeData"]["object"]["info"][
                "PhaseEncodingDirection"
            ]
            pedir_pos = tr("ijk", "xyz", pedir_pos)
            pedir_neg = tr("ijk", "xyz", pedir_neg)
            if pedir_pos == pedir_neg:
                raise Exception(
                    "DWIPositive and DWINegative must have "
                    + "opposite phase-encoding directions."
                )
            elif not (
                ((pedir_pos, pedir_neg) == ("x-", "x"))
                or ((pedir_pos, pedir_neg) == ("x", "x-"))
                or ((pedir_pos, pedir_neg) == ("y-", "y"))
                or ((pedir_pos, pedir_neg) == ("y", "y-"))
            ):
                raise Exception(
                    "DWIPositive and DWINegative have unrecognized "
                    + "phase-encoding directions"
                )
        else:
            raise Exception(
                "DWIPositive or DWINegative input data is missing "
                + "PhaseEncodingDirection metadata!"
            )
    else:
        raise Exception("DWIPositive or DWINegative input data is missing!")

    # Loop through the individual Diffusion files
    for i in range(1, 11):
        # i=1 is a special case here
        # the list of Diffusion files follows the format of
        # DWIPositiveData, DWIPositiveData2, ...3, ....
        if i == 1:
            j = ""
        else:
            j = i
        # We only add to posData and negData if both are present
        # If only one is present, warn them in validate()
        if ("DWIPositiveData{}".format(j) in inputs.keys()) and (
            "DWINegativeData{}".format(j) in inputs.keys()
        ):
            # Grab the Phase Encoding
            info_pos = inputs["DWIPositiveData{}".format(j)]["object"]["info"]
            info_neg = inputs["DWINegativeData{}".format(j)]["object"]["info"]
            if ("PhaseEncodingDirection" in info_pos.keys()) and (
                "PhaseEncodingDirection" in info_neg.keys()
            ):
                PE_pos = tr("ijk", "xyz", info_pos["PhaseEncodingDirection"])
                PE_neg = tr("ijk", "xyz", info_neg["PhaseEncodingDirection"])
            else:
                raise Exception(
                    "DWIPositiveData%i or DWINegativeData%i "
                    'is missing "PhaseEncodingDirection"!',
                    j,
                    j,
                )

            # Grab each of the pos/neg bvec/bval files or make them None
            if "DWIPositiveBvec{}".format(j) not in inputs.keys():
                raise Exception(
                    "DWIPositiveBvec{} is missing! Please include".format(j)
                    + " as an input before proceeding."
                )

            if "DWINegativeBvec{}".format(j) not in inputs.keys():
                raise Exception(
                    "DWINegativeBvec{} is missing! Please include".format(j)
                    + " as an input before proceeding."
                )

            if "DWIPositiveBval{}".format(j) not in inputs.keys():
                raise Exception(
                    "DWIPositiveBval{} is missing! Please include".format(j)
                    + " as an input before proceeding."
                )

            if "DWINegativeBval{}".format(j) not in inputs.keys():
                raise Exception(
                    "DWINegativeBval{} is missing! Please include".format(j)
                    + " as an input before proceeding."
                )

            if PE_pos == PE_neg:
                raise Exception(
                    "DWIPositiveData%i and DWINegativeData%i have "
                    "the same PhaseEncodingDirection (%s)!",
                    j,
                    j,
                    PE_pos,
                )
            elif not (
                ((pedir_pos, pedir_neg) == (PE_pos, PE_neg))
                or ((pedir_pos, pedir_neg) == (PE_neg, PE_pos))
            ):
                raise Exception(
                    "DWI input pair #${} phase-encoding directions ".format(j)
                    + "({},{}) do not match primary ".format(PE_pos, PE_neg)
                    + "pair ({},{}). Exiting!".format(pedir_pos, pedir_neg)
                )

        # Warn of the Exclusive OR (XOR) case
        elif ("DWIPositiveData{}".format(j) in inputs.keys()) ^ (
            "DWINegativeData{}".format(j) in inputs.keys()
        ):
            log.warning(
                "Only one of DWIPositiveData%i or "
                "DWINegativeData%i "
                "was selected. Thus none of their related data is included "
                "in this analysis.",
                j,
                j,
            )

    if "DWIPositiveData" in inputs.keys():
        info = inputs["DWIPositiveData"]["object"]["info"]
        if "EffectiveEchoSpacing" not in info.keys():
            raise Exception(
                '"EffectiveEchoSpacing" is not found in DWIPositiveData. '
                + "This is required to continue! Exiting."
            )


def execute(context):
    # We want to take care of delivering the directory structure right away
    # when we unzip the hcp-struct zip
    environ = context.gear_dict["environ"]
    config = context.config
    os.makedirs(context.work_dir + "/" + config["Subject"], exist_ok=True)

    # Start by building command to execute
    command = []
    command.extend(context.gear_dict["command_common"])
    command.append(
        op.join(
            environ["HCPPIPEDIR"], "DiffusionPreprocessing", "DiffPreprocPipeline.sh"
        )
    )
    command = build_command_list(command, context.gear_dict["Diff-params"])

    stdout_msg = (
        "Pipeline logs (stdout, stderr) will be available "
        + 'in the file "pipeline_logs.zip" upon completion.'
    )

    log.info("GenericfMRIVolumeProcessingPipeline command: \n")
    exec_command(context, command, stdout_msg=stdout_msg)
