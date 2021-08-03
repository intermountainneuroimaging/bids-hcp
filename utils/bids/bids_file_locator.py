import logging
import os.path as op
import subprocess as sp

from bids.layout import BIDSLayout #pybids
from bids_hcp.utils import gear_arg_utils
from bids_hcp.utils.bids import run_level, validate, download_run_level
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.utils.config import Config

log = logging.getLogger(__name__)


class bidsInput:
    def __init__(self, context: GearToolkitContext):
        self.gtk_context = context
        self.config = self.gtk_context.config_json
        self.hierarchy = run_level.get_run_level_and_hierarchy(
            self.gtk_context.client, self.gtk_context.destination["id"]
        )

    def gather_bids_files(self):
        """
        Update the config.json to mimic user input that typically would have occurred
        without this BIDS locator. That entails tracking down the file types and loading them
        into the context variable
        Args:
            gtk_context (GearToolkitContext): Initial gear context, including sparse user inputs

        Returns:
            Updated config.json file to feed into the main gear modules as if the user had input the values.
        """

        # Populate the gear args with the configuration options right off the bat
        self.gear_args = gear_arg_utils(self.config)
        self.gear_args.update = gear_arg_utils(self.gtk_context.inputs)
        self.gear_args['bids_dir'] = op.join(self.gear_args['work_dir'], 'bids')

        # Download the BIDS curated data and validate here to reduce compute for faulty runs
        msg = self.grab_BIDS_data()
        log.info(msg)
        # Use pyBIDS finder method to capture the BIDS structure for these data
        self.layout = BIDSLayout(
            bids_dir, validate=self.gear_args['gear-run-bids-validation'], derivatives=False, absolute_paths=True
        )

        # Search the layout for the different modality types
        # TODO add a session filter (These go at the end of the t1ws and t2ws calls to layout.get)

        # Each stage seems to require structural scans. Find them before anything else.
        self.find_t1ws()
        self.find_t2ws()

        if "struct" in self.gear_args["stages"]:
            self.find_struct_fieldmaps()
        if "func" in self.gear_args["stages"]:
            self.find_func_fieldmaps()
            self.define_bolds()
        if "diff" in self.gear_args["stages"]:
            self.find_dwis()

        # For the cases where structural was initially completed and probably zipped.
        if "struct" not in self.gear_args["stages"]:
            # find the T1 results
            # unzip them
            # Set the T1 filepath for func and/or diff to use


    def find_t1ws(self):
        """
        Locate the structural scans to be processed.
        """
        self.t1ws = [
            f.path
            for f in self.layout.get(
                subject=self.hierarchy.subject_label,
                suffix="T1w",
                extensions=["nii.gz", "nii"],
            )
        ]
        assert len(self.t1ws) > 0, (
            "No T1w files found for subject %s!" % self.hierarchy.subject_label
        )
        self.gear_args['struct']['raw_T1s'] = self.t1ws

    def find_t2ws(self):
        self.t2ws = [
            f.path for f in self.layout.get(subject=self.subject_label, suffix="T2w")
        ]
        self.gear_args['struct']['raw_T2s'] = self.t2ws

    def find_struct_fieldmaps(self, bids_dir):
        if not self.t1ws:
            self.find_t1ws()

        fieldmap_set = self.layout.get_fieldmap(self.t1ws[0], return_list=True)
        if fieldmap_set[0]["suffix"] == "phasediff":
            # Create Siemens style Magnitude and Phase
            merged_file = "%s/tmp/%s/magfile.nii.gz" % (
                self.gears_args['bids_dir'],
                self.hierarchy.subject_label,
            )
            sp.run(
                [
                    "mkdir",
                    "-p",
                    op.join(self.gears_args['bids_dir'], self.hierarchy.subject_label),
                    "&&",
                    "fslmerge",
                    "-t",
                    merged_file,
                    fieldmap_set["magnitude1"],
                    fieldmap_set["magnitude2"],
                ]
            )

            phasediff_metadata = self.layout.get_metadata(fieldmap_set["phasediff"])
            te_diff = phasediff_metadata["EchoTime2"] - phasediff_metadata["EchoTime1"]
            # HCP expects TE in miliseconds
            self.gear_args['struct']['te_diff'] = te_diff * 1000.0

            self.gear_args['struct'].update(
                {
                    "fmapmag": merged_file,
                    "fmapphase": fieldmap_set["phasediff"],
                    "echodiff": "%.6f" % te_diff,
                    "avgrdcmethod": "SiemensFieldMap",
                }
            )

    def find_func_fieldmaps(self):
        if not self.t1ws:
            self.find_t1ws()

        fieldmap_set = self.layout.get_fieldmap(self.t1ws[0], return_list=True)
        if fieldmap_set[0]["suffix"] == "epi":
            SEPhaseNeg = None
            SEPhasePos = None
            for fieldmap in fieldmap_set:
                enc_dir = self.layout.get_metadata(fieldmap["epi"])[
                    "PhaseEncodingDirection"
                ]
                if "-" in enc_dir:
                    SEPhaseNeg = fieldmap["epi"]
                else:
                    SEPhasePos = fieldmap["epi"]

            seunwarpdir = self.layout.get_metadata(fieldmap_set[0]["epi"])[
                "PhaseEncodingDirection"
            ]
        # TODO check if the seunwarpdir is a BIDS app or HCP arg; capitalization??
        self.gear_args['func'].update(
            {
                "SEPhaseNeg": SEPhaseNeg,
                "SEPhasePos": SEPhasePos,
                "seunwarpdir": seunwarpdir,
            }
        )

    def find_bolds(self):
        # TODO add session filter here especially
        self.bolds = [
            f.path
            for f in self.layout.get(subject=self.hierarchy.subject_label, suffix="bold")
        ]
        for fmritcs in self.bolds:
            fmriname = "_".join(fmritcs.split("sub-")[-1].split("_")[1:]).split(".")[0]
            assert fmriname

        # TODO valid for FLywheel's curations?
        fmriscout = fmritcs.replace("_bold", "_sbref")
        if not os.path.exists(fmriscout):
            fmriscout = "NONE"

        fieldmap_set = self.layout.get_fieldmap(fmritcs, return_list=True)
        if (
            fieldmap_set
            and len(fieldmap_set) == 2
            and all(item["suffix"] == "epi" for item in fieldmap_set)
            and (self.config.processing_mode != "legacy")
        ):
            # TODO add different processing modes to manifest?
            SEPhaseNeg = None
            SEPhasePos = None
            for fieldmap in fieldmap_set:
                enc_dir = self.layout.get_metadata(fieldmap["epi"])[
                    "PhaseEncodingDirection"
                ]
            if "-" in enc_dir:
                SEPhaseNeg = fieldmap["epi"]
            else:
                SEPhasePos = fieldmap["epi"]
        # TODO check here for collisions in parameters too.
        self.gear_args['func'].update(
            {"fmriscout": fmriscout, "SEPhasePos": SEPhasePos, "SEPhaseNeg": SEPhaseNeg}
        )

    def find_dwis(self):
        dwis = self.layout.get(subject=self.hierarchy.subject_label, suffix="dwi")
        numruns = set(
            self.layout.get(
                target="run", return_type="id", subject=self.hierarchy.subject_label, type="dwi"
            )
        )
        # accounts for multiple runs, number of directions, and phase encoding directions

        # TODO figure out what is intended by looking for multiple runs

        if numruns:
            ## find number of directions by reading bval files, then create dictionary with corresponding
            # bval file name, number of directions, dwi image file name, and phase encoding direction (i or j).
            dwi_dict = {"bvalFile": [], "bval": [], "dwiFile": [], "direction": []}
            if len(numruns) == 1:
                bvals = [
                    f.filename
                    for f in self.layout.get(
                        subject=self.hierarchy.subject_label, type="dwi", run=numrun
                    )
                ]
            else:
                for numrun in numruns:
                    bvals = [
                        f.filename
                        for f in self.layout.get(
                            subject=self.hierarchy.subject_label, type="dwi", extensions=["bval"]
                        )
                    ]
           # TODO differentiate between bvec and bval, since extensions arg no longer valid
            for bvalfile in bvals:  # find number of directions
                with open(bvalfile) as f:
                    bvalues = [bvalue for line in f for bvalue in line.split()]
                # fill in the rest of dictionary
                dwi_dict["bvalFile"].append(bvalfile)
                dwi_dict["bval"].append(len(bvalues) - 1)
                dwiFile = glob(
                    op.join(
                        op.dirname(bvalfile),
                        "{0}.nii*".format(op.basename(bvalfile).split(".")[0]),
                    )
                )  # ensures bval file has same name as dwi file
                assert len(dwiFile) == 1
                dwi_dict["dwiFile"].append(dwiFile[0])
                dwi_dict["direction"].append(
                    self.layout.get_metadata(dwiFile[0])["PhaseEncodingDirection"][0]
                )

                # check if length of lists in dictionary are the same
                n = len(dwi_dict["bvalFile"])
                assert all(len(dwi_dict[k]) == n for k, v in dwi_dict.items())

                for dirnum in set(dwi_dict["bval"]):
                    ## the following statement extracts index values in dwi_dict['bval'] if the value matches
                    # "dirnum", which is the number of directions (i.e. 98 or 99). These index values are used
                    # to find the corresponding PE directions, dwi file names, etc. in the dictionary
                    idxs = {
                        i
                        for k, v in dwi_dict.iteritems()
                        for i in range(0, len(dwi_dict["bval"]))
                        if v[i] == dirnum
                    }
                    PEdirNums = set([dwi_dict["direction"][i] for i in idxs])
                    for PEdirNum in PEdirNums:
                        dwis = [
                            dwi_dict["dwiFile"][i]
                            for i in idxs
                            if dwi_dict["direction"][i] == PEdirNum
                        ]
                        assert len(dwis) <= 2
                        dwiname = (
                            "Diffusion"
                            + "_dir-"
                            + str(dirnum)
                            + "_"
                            + numrun
                            + "_corr_"
                            + str(PEdirNum)
                        )
                        if "j" in PEdirNum:
                            PEdir = 2
                        elif "i" in PEdirNum:
                            PEdir = 1
                        else:
                            RuntimeError(
                                "Phase encoding direction not specified for diffusion data."
                            )
                        pos = "EMPTY"
                        neg = "EMPTY"
                        gdcoeffs = "None"
                        for dwi in dwis:
                            if (
                                "-"
                                in self.layout.get_metadata(dwi)["PhaseEncodingDirection"]
                            ):
                                neg = dwi
                            else:
                                pos = dwi

                            echospacing = (
                                self.layout.get_metadata(pos)["EffectiveEchoSpacing"] * 1000
                            )

                self.gear_args['diff'].update(
                    {
                        "dwiname": dwiname,
                        "PEdir": PEdir,
                        "pos": pos,
                        "neg": neg,
                        "echospacing": echospacing,
                    }
                )
                #TODO Is the dwi_dict used?

    def grab_BIDS_data(self):
        """
        Download and validate the BIDS directory structure from curated data.
        This method must be included since the files are copied up to Docker and the
        file organization will need to follow the BIDS curation/specification.
        Args:
            gtk_context (GearToolkitContext): gear information
        Returns:
            msg (str): Status of BIDS download (and validation)
        """
        log.info("Checking BIDS")
        config = self.gtk_context.config
        try:
            log.info("Downloading BIDS")
            bids_e_code = download_bids_for_runlevel(
                self.gtk_context,
                self.hierarchy,
                do_validate_bids=self.config['gear-run-bids-validation']
            )
            if bids_e_code == 0:
                msg = "BIDS download completed with no errors."
            else:
                msg = f'BIDS download encountered {bids_e_code} in download_bids_for_runlevel'
        except Exception as e:
            log.error(
                f'Could not download BIDS data from {self.gtk_context.work_dir / "bids"}'
            )
            log.exception(e)
            msg = "Errors in BIDS download."

        if config["gear-run-bids-validation"] and config["gear-abort-on-bids-error"]:
            # Pass the BIDS dir to the commandline BIDS validator that virtually all BIDS apps
            # use and check for errors.
            # Error logging handled within validate_bids.

            # Need to convert from cli to python bids_validator (npm unstable solution)
            # bids.layout.BIDSValidator is essentially the same
            # validate.validate_bids(self.gtk_context)
            msg = "BIDS download and validation complete."
        return msg

    def update_struct_zip(self):
        """
        The structural stage of this gear zips the output. The functional and diffusion stages
        (as originally written) require that zip file.
        Args:
            context object
        Returns:
            modified context object with file path to zipped structural outputs.
        """
        pass

