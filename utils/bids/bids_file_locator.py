import logging
import os
import os.path as op
import re
import subprocess as sp
from glob import glob

import nibabel
from bids.layout import BIDSLayout  # pybids
from flywheel_gear_toolkit import GearToolkitContext

from utils import gear_arg_utils, helper_funcs
from utils.bids import download_run_level, run_level, validate

log = logging.getLogger(__name__)


class bidsInput:
    def __init__(self, gtk_context: GearToolkitContext):
        """Instantiates self.gtk_context and retrieves organizational
        information about the type of image selected for analysis."""
        self.gtk_context = gtk_context
        self.config = self.gtk_context.config_json
        self.hierarchy = run_level.get_analysis_run_level_and_hierarchy(
            self.gtk_context.client, self.gtk_context.destination["id"]
        )
        self.layout = None
        self.t1ws = None
        self.t2ws = None

    def find_bids_files(self, gear_args):
        """
        Update the config.json to mimic user input that typically would have occurred
        without this BIDS locator. That entails tracking down the file types and loading them
        into the context variable
        Args:
            gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters

        Returns:
            Updated config.json file to feed into the main gear modules as if the user had input the values.
        """
        # Download the BIDS curated data and validate here to reduce compute for faulty runs
        msg = self.download_and_validate_BIDS_data()
        log.info(msg)

        # If structural analysis is complete, grab it and unzip.
        if "hcpstruct_zip" in self.config["inputs"]:
            gear_args.common["hcpstruct_zip"] = self.gtk_context.get_input_path(
                "hcpstruct_zip"
            )
        if "gdcoeffs" in self.config["inputs"]:
            gear_args.common["gdcoeffs"] = self.gtk_context.get_input_path("gdcoeffs")
            if re.search(gear_args.common["gdcoeffs"], " +"):
                new_name = "_".join(gear_args.common["gdcoeffs"].split(" "))
                os.rename(gear_args.common["gdcoeffs"], new_name)
                gear_args.common["gdcoeffs"] = new_name

        # Use pyBIDS finder method to capture the BIDS structure for these data
        self.layout = BIDSLayout(
            gear_args.dirs["bids_dir"],
            validate=gear_args.fw_specific["gear_run_bids_validation"],
            derivatives=False,
            absolute_paths=True,
        )

        # Each stage seems to require structural scans. Find them before anything else.
        self.find_t1ws(gear_args)
        self.find_t2ws(gear_args)
        # Fieldmaps are located and manipulated, if necessary, with verify.dcmethods

        if any("fmri" in arg.lower() for arg in [gear_args.common["stages"]]):
            self.find_bolds(gear_args)
            (
                n,
                p,
                gear_args.functional["unwarp_dir"],
                gear_args.functional["echo_spacing"],
            ) = self.read_PE_dir(gear_args.functional["fmri_timecourse_all"])
        if any("Diffusion" in arg for arg in [gear_args.common["stages"]]):
            self.find_dwis(gear_args)

    def find_t1ws(self, gear_args):
        """
        Locate the T1-weighted structural scans to be processed.
        """
        self.t1ws = [
            f.path
            for f in self.layout.get(
                subject=self.hierarchy["subject_label"].split("-")[-1],
                suffix="T1w",
                extension=["nii.gz", "nii"],
            )
        ]
        self.t1ws = [
            scan
            for scan in self.t1ws
            if "MNINonLinear" not in scan
        ]
        assert len(self.t1ws) > 0, (
            "No T1w files found for subject %s!"
            % self.hierarchy["subject_label"].split("-")[-1]
        )
        gear_args.structural["raw_t1s"] = self.t1ws

    def find_t2ws(self, gear_args):
        """Locate T2-weighted images to be processed."""
        self.t2ws = [
            f.path
            for f in self.layout.get(
                subject=self.hierarchy["subject_label"].split("-")[-1],
                suffix="T2w",
                extension=["nii.gz", "nii"],
            )
        ]
        self.t2ws = [
            scan
            for scan in self.t2ws
            if "MNINonLinear" not in scan
        ]
        gear_args.structural["raw_t2s"] = self.t2ws

    def find_bolds(self, gear_args):
        """Locate the functional (EPI) images to be processed."""
        # only use a subset of sessions
        if "session_label" in gear_args.common.keys():
            sessions_to_analyze = dict(session=gear_args.common["session_label"])
        else:
            sessions_to_analyze = dict()

        gear_args.functional["fmri_timecourse_all"] = [
            f.path
            for f in self.layout.get(
                subject=self.hierarchy["subject_label"].split("-")[-1],
                suffix="bold",
                extension=["nii.gz", "nii"],
                **sessions_to_analyze,
            )
        ]
        # HCPStruct pre-existing, normalized images filter
        gear_args.functional["fmri_timecourse_all"] = [
            scan
            for scan in gear_args.functional["fmri_timecourse_all"]
            if "MNINonLinear" not in scan
        ]
        # Custom filters
        for label in ("task_label", "run_label"):
            if label in gear_args.common.keys():
                tmp = []
                if not isinstance(gear_args.common[label], list):
                    gear_args.common[label] = gear_args.common[label].split()
                for item in gear_args.common[label]:
                    tmp.append(
                        [
                            scan
                            for scan in gear_args.functional["fmri_timecourse_all"]
                            if label.split("_")[0] + "-" + item in scan
                        ]
                    )
                gear_args.functional["fmri_timecourse_all"] = [
                    scan for scan_list in tmp for scan in scan_list
                ]

        # Important check. Do not want to make the tmp.append a regex, b/c you could get into a loop for run 1, 10, 01, 010, etc.
        if not gear_args.functional["fmri_timecourse_all"]:
            log.error(
                f'Did not find any files matching {label.split("_")[0] + "-" + item }\nPlease make sure the run_label and task_label in the config matches the BIDS name precisely.'
            )
            os.sys.exit(1)

        # Each fMRI acquisition should have a corresponding scout
        names = []
        gear_args.functional["fmri_scouts_all"] = []
        for fmri_timecourse in gear_args.functional["fmri_timecourse_all"]:
            name = "_".join(fmri_timecourse.split("sub-")[-1].split("_")[1:]).split(
                "."
            )[0]
            assert name
            names.append(name)
            if op.exists(fmri_timecourse.replace("_bold", "_sbref")):
                gear_args.functional["fmri_scouts_all"].append(
                    fmri_timecourse.replace("_bold", "_sbref")
                )
            else:
                # Set scout to NONE for any acquisition that does not have an sbref. Possible TODO: allow one sbref to be defined for all EPIs
                gear_args.functional["fmri_scouts_all"].append("NONE")

        gear_args.functional["fmri_names"] = names

    def find_dwis(self, gear_args):
        """Locate the diffusion weighted images to be processed."""
        gear_args.diffusion["raw_dwis"] = self.layout.get(
            subject=self.hierarchy["subject_label"].split("-")[-1],
            suffix="dwi",
            extension=["nii.gz", "nii"],
        )
        # HCPStruct filter differs from func, b/c structure of iterator is different.
        gear_args.diffusion["raw_dwis"] = [
            scan
            for scan in gear_args.diffusion["raw_dwis"]
            if "MNINonLinear" not in scan.filename
        ]
        if gear_args.diffusion["raw_dwis"]:
            directions = set(
                self.layout.get(
                    target="acquisition",
                    return_type="id",
                    subject=self.hierarchy["subject_label"].split("-")[-1],
                    datatype="dwi",
                    extension=["nii.gz", "nii"],
                )
            )

            gear_args.diffusion["pos_data"] = []
            gear_args.diffusion["neg_data"] = []
            num_of_directions = len(directions)
            for i, enc_dir in enumerate(sorted(directions)):
                matching_files = [
                    f.path
                    for f in gear_args.diffusion["raw_dwis"]
                    if enc_dir in f.filename
                ]
                # Not crazy - the diffusion directions are opposite. Neg is first.
                neg, pos, _, echo_spacing = self.read_PE_dir(matching_files)
                gear_args.diffusion["pos_data"].append(pos)
                gear_args.diffusion["neg_data"].append(neg)
                ################### From HCP example script
                # NOTE that pos_data defines the reference space in 'topup' and 'eddy' AND it is assumed that
                # each scan series begins with a b=0 acquisition, so that the reference space in both
                # 'topup' and 'eddy' will be defined by the same (initial b=0) volume.
                ###################
                if i == 0:
                    gear_args.diffusion["echo_spacing"] = echo_spacing
                    # Find the PE_dir of that file
                    # --PE_dir = < phase-encoding-dir >  phase encoding direction specifier: 1 = LR / RL, 2 = AP / PA
                    if ("AP" in pos) or ("PA" in pos):
                        gear_args.diffusion["PE_dir"] = 2
                    else:
                        gear_args.diffusion["PE_dir"] = 1

            assert gear_args.diffusion["PE_dir"]
            # Pairs of opposite polarities are needed for the algorithm. Check for matches here
            log.debug(
                f'Number of positive and negative DWI acquisitions match: {len(gear_args.diffusion["pos_data"]) == len(gear_args.diffusion["neg_data"])}'
            )
            assert len(gear_args.diffusion["pos_data"]) == len(
                gear_args.diffusion["neg_data"]
            )
            assert len(gear_args.diffusion["pos_data"]) == num_of_directions
            gear_args.diffusion.update({"combine_data_flag": 1})

        else:
            log.error(
                f'No DWI files were located for {self.hierarchy["subject_label"]}.\n'
                f'Please verify acquisitions, BIDS curation, and then select "stages" '
                f"for analysis."
            )

    def download_and_validate_BIDS_data(self):
        """
        Download and validate the BIDS directory structure from curated data.
        This method must be included since the files are copied up to Docker and the
        file organization will need to follow the BIDS curation/specification.

        Returns:
            msg (str): Status of BIDS download (and validation)
        """
        log.info("Checking BIDS")
        config = self.gtk_context.config
        try:
            bids_e_code = download_run_level.download_bids_for_runlevel(
                self.gtk_context,
                self.hierarchy,
                src_data=False,
                tree=True,
                do_validate_bids=config["gear_run_bids_validation"],
            )
            if bids_e_code == 0 or not bids_e_code:
                msg = "BIDS download completed with no errors."
            else:
                msg = f"BIDS download encountered {bids_e_code} in download_bids_for_runlevel"
        except Exception as e:
            log.error(
                f'Could not download BIDS data from {self.gtk_context.work_dir / "bids"}'
            )
            log.exception(e)
            msg = "Errors in BIDS download."

        if config["gear_run_bids_validation"] and config["gear_abort_on_bids_error"]:
            # Pass the BIDS dir to the commandline BIDS validator that virtually all BIDS apps
            # use and check for errors.
            # Error logging handled within validate_bids.
            validate.validate_bids(self.gtk_context)
            msg = "BIDS download and validation complete."
        return msg

    def read_PE_dir(self, img_list):
        """
        Phase encoding direction needs to be validated for any number of acquisitions. This method
        reads the header information to determine the positive and negative directions to
        supply back to the HCP algorithm.
        Args:
            img_list: BIDSLayout image list (e.g., fieldmap_set)

        Returns:
            List of positive and negative images (e.eg., SEPos, SENeg) along with the
            unwarp direction and echo spacing settings
        """
        phase_neg = None
        phase_pos = None
        try:
            for img in img_list:
                unwarp_dir = "undefined"
                try:
                    enc_dir = self.layout.get_metadata(img)["PhaseEncodingDirection"]
                    if "-" in enc_dir:
                        phase_neg = img
                    else:
                        phase_pos = img
                    try:
                        unwarp_dir = (
                            enc_dir.replace("-", "")
                            .replace("i", "x")
                            .replace("j", "y")
                            .replace("k", "z")
                        )
                    except Exception as e:
                        log.debug(f"unwarp_dir undetermined for {img}")
                        log.exception(e)
                except Exception as e:
                    log.debug(f"Checking PE dir produced\n{e}")

                echo_spacing = "undefined"

                if "EffectiveEchoSpacing" in self.layout.get_metadata(img):
                    echo_spacing = format(
                        self.layout.get_metadata(img)["EffectiveEchoSpacing"] * 1000,
                        ".15f",
                    )
                elif "TotalReadoutTime" in self.layout.get_metadata(img):
                    # HCP Pipelines do not allow users to specify total readout time directly
                    # Hence we need to reverse the calculations to provide echo spacing that would
                    # result in the right total read out total read out time
                    # see https://github.com/Washington-University/Pipelines/blob/master/global/scripts/TopupPreprocessingAll.sh#L202
                    log.info(
                        "Did not find EffectiveEchoSpacing, calculating it from TotalReadoutTime"
                    )
                    # TotalReadoutTime = EffectiveEchoSpacing * (len(PhaseEncodingDirection) - 1)
                    total_readout_time = self.layout.get_metadata(img)[
                        "TotalReadoutTime"
                    ]
                    phase_len = nibabel.load(img).shape[{"x": 0, "y": 1}[unwarp_dir]]
                    echo_spacing = total_readout_time / float(phase_len - 1)
                else:
                    log.error(
                        f"RuntimeError: EffectiveEchoSpacing or TotalReadoutTime not defined for the fieldmap intended for {op.basename(img)}. The fieldmap is required, please fix your BIDS dataset."
                    )
            return phase_neg, phase_pos, unwarp_dir, echo_spacing
        except UnboundLocalError as e:
            # Cannot continue without an unwarp_dir or valid image list.
            log.debug("Empty image list. Check the BIDS curation.")
            log.exception(e)
