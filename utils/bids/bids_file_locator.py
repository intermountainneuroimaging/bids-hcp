import logging
import os.path as op
import subprocess as sp

from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.utils.config import Config
from bids.layout import BIDSLayout

from bids_hcp_struct.utils.bids import validate, run_level

from .custom_logger import get_custom_logger

log = logging.getLogger(__name__)

class bidsInput:
    def __init__(self, pth=None):
        if pth:
            self.gtk_context = GearToolkitContext(config_path=pth)
        else:
            self.gtk_context = GearToolkitContext()
        self.config = self.gtk_context.config_json
        self.hierarchy = run_level.get_run_level_and_hierarchy(self.gtk_context.client, self.gtk_context.destination['id'])

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

        bids_dir = op.join(self.gtk_context.work_dir, 'bids')
        msg = self.grab_BIDS_data()
        log.info(msg)
        #TODO add validate={config_option}
        self.layout = BIDSLayout(bids_dir, validate=False, derivatives=False, absolute_paths=True)

        # Find the sub-* directories

        # TODO add a session filter (These go at the end of the t1ws nad t2ws args)



    def find_t1ws(self):
        self.t1ws = [f.path for f in self.layout.get(subject=self.hierarchy.subject_label,
                                               suffix='T1w',
                                               extensions=["nii.gz", "nii"])]
        assert (len(self.t1ws) > 0), "No T1w files found for subject %s!"%self.hierarchy.subject_label
        # TODO set the context inputs["T1"] to t1ws

    def find_t2ws(self):
        self.t2ws = [f.path for f in self.layout.get(subject=self.subject_label,
                                           suffix='T2w')]
        # TODO set the context inputs["T2"] to t2ws

    def find_struct_fieldmaps(self, bids_dir):
        fieldmap_set = self.layout.get_fieldmap(self.t1ws[0], return_list=True)
        if fieldmap_set[0]["suffix"] == "phasediff":
            # Create Siemens style Magnitude and Phase
            merged_file = "%s/tmp/%s/magfile.nii.gz" % (bids_dir, self.hierarchy.subject_label)
            sp.run(["mkdir", "-p", op.join(bids_dir, self.hierarchy.subject_label),
                   '&&', 'fslmerge', '-t', merged_file,
                    fieldmap_set["magnitude1"], fieldmap_set["magnitude2"]
                    ])

            phasediff_metadata = self.layout.get_metadata(fieldmap_set["phasediff"])
            te_diff = phasediff_metadata["EchoTime2"] - phasediff_metadata["EchoTime1"]
            # HCP expects TE in miliseconds
            te_diff = te_diff * 1000.0

            config.update({"fmapmag": merged_file,
                              "fmapphase": fieldmap_set["phasediff"],
                              "echodiff": "%.6f" % te_diff,
                              "avgrdcmethod": "SiemensFieldMap"})

    def find_func_fieldmaps(self):
        fieldmap_set = self.layout.get_fieldmap(self.t1ws[0], return_list=True)
        if fieldmap_set[0]["suffix"] == "epi":
            SEPhaseNeg = None
            SEPhasePos = None
            for fieldmap in fieldmap_set:
                enc_dir = self.layout.get_metadata(fieldmap['epi'])["PhaseEncodingDirection"]
                if "-" in enc_dir:
                    SEPhaseNeg = fieldmap['epi']
                else:
                    SEPhasePos = fieldmap['epi']

            seunwarpdir = self.layout.get_metadata(fieldmap_set[0]["epi"])["PhaseEncodingDirection"]

    #def find_bolds():
            # bolds = [f.path for f in layout.get(subject=subject_label,
            #                                     suffix='bold',
            #                                     extensions=["nii.gz", "nii"],
            #                                     **session_to_analyze)
            #          for fmritcs in bolds:
            # fmriname = "_".join(fmritcs.split("sub-")[-1].split("_")[1:]).split(".")[0]
            # assert fmriname
            #
            # fmriscout = fmritcs.replace("_bold", "_sbref")
            # if not os.path.exists(fmriscout):
            #     fmriscout = "NONE"
            #
            # fieldmap_set = layout.get_fieldmap(fmritcs, return_list=True)
            # if fieldmap_set and len(fieldmap_set) == 2 and all(item["suffix"] == "epi" for item in fieldmap_set) and (
            #         args.processing_mode != 'legacy'):
            #     SEPhaseNeg = None
            #     SEPhasePos = None
            #     for fieldmap in fieldmap_set:
            #         enc_dir = layout.get_metadata(fieldmap["epi"])["PhaseEncodingDirection"]
            #     if "-" in enc_dir:
            #         SEPhaseNeg = fieldmap['epi']
            #     else:
            #         SEPhasePos = fieldmap['epi']

    #def find_dwis():
            # dwis = layout.get(subject=subject_label, suffix='dwi',
            #                   extensions=["nii.gz", "nii"])
            # numruns = set(layout.get(target='run', return_type='id',
            #                          subject=subject_label, type='dwi',
            #                          extensions=["nii.gz", "nii"]))
            # # accounts for multiple runs, number of directions, and phase encoding directions
            #
            # if numruns:
            #     for numrun in numruns:
            #         if not onerun:
            #             bvals = [f.filename for f in layout.get(subject=subject_label,
            #                                                     type='dwi', run=numrun,
            #                                                     extensions=["bval"])]
            #         else:
            #             bvals = [f.filename for f in layout.get(subject=subject_label,
            #                                                     type='dwi', extensions=["bval"])]
            #         ## find number of directions by reading bval files, then create dictionary with corresponding
            #         # bval file name, number of directions, dwi image file name, and phase encoding direction (i or j).
            #         dwi_dict = {'bvalFile':[], 'bval':[], 'dwiFile':[], 'direction':[]}
            #         for bvalfile in bvals: # find number of directions
            #             with open(bvalfile) as f:
            #                 bvalues = [bvalue for line in f for bvalue in line.split()]
            #             # fill in the rest of dictionary
            #             dwi_dict['bvalFile'].append(bvalfile)
            #             dwi_dict['bval'].append(len(bvalues) - 1)
            #             dwiFile = glob(os.path.join(os.path.dirname(bvalfile),'{0}.nii*'.format(os.path.basename(bvalfile).split('.')[0]))) # ensures bval file has same name as dwi file
            #             assert len(dwiFile) == 1
            #             dwi_dict['dwiFile'].append(dwiFile[0])
            #             dwi_dict['direction'].append(layout.get_metadata(dwiFile[0])["PhaseEncodingDirection"][0])
            #
            #         # check if length of lists in dictionary are the same
            #         n = len(dwi_dict['bvalFile'])
            #         assert all(len(dwi_dict[k]) == n for k,v in dwi_dict.items())
            #
            #         for dirnum in set(dwi_dict['bval']):
            #             ## the following statement extracts index values in dwi_dict['bval'] if the value matches
            #             # "dirnum", which is the number of directions (i.e. 98 or 99). These index values are used
            #             # to find the corresponding PE directions, dwi file names, etc. in the dictionary
            #             idxs = { i for k,v in dwi_dict.iteritems() for i in range(0,len(dwi_dict['bval'])) if v[i] == dirnum }
            #             PEdirNums = set([dwi_dict['direction'][i] for i in idxs])
            #             for PEdirNum in PEdirNums:
            #                 dwis = [ dwi_dict['dwiFile'][i] for i in idxs if dwi_dict['direction'][i] == PEdirNum ]
            #                 assert len(dwis) <= 2
            #                 dwiname = "Diffusion" + "_dir-" + str(dirnum) + "_" + numrun + "_corr_" + str(PEdirNum)
            #                 if "j" in PEdirNum:
            #                     PEdir = 2
            #                 elif "i" in PEdirNum:
            #                     PEdir = 1
            #                 else:
            #                     RuntimeError("Phase encoding direction not specified for diffusion data.")
            #                 pos = "EMPTY"
            #                 neg = "EMPTY"
            #                 gdcoeffs = "None"
            #                 for dwi in dwis:
            #                     if "-" in layout.get_metadata(dwi)["PhaseEncodingDirection"]:
            #                         neg = dwi
            #                     else:
            #                         pos = dwi
            #
            #                     echospacing = layout.get_metadata(pos)["EffectiveEchoSpacing"] * 1000


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
            log.info('Downloading BIDS')
            self.gtk_context.download_session_bids(target_dir=self.gtk_context.work_dir / "bids")
            msg = "BIDS downloaded, but validation was not required."
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
            #validate.validate_bids(self.gtk_context)
            msg = "BIDS download and validation complete."
        return msg
