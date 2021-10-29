[![Docker Pulls](https://img.shields.io/docker/pulls/flywheel/hcp-struct.svg)](https://hub.docker.com/r/flywheel/hcp-struct/)
[![Docker Stars](https://img.shields.io/docker/stars/flywheel/hcp-struct.svg)](https://hub.docker.com/r/flywheel/hcp-struct/)
  
# OVERVIEW
BIDS HCP wraps all the major stages of processing outlined in the minimally processed pipeline. Specific notes about processing each methodology are listed below.

## Specific notes
Devs: When beginning work with this gear, please take a close look at utils.set_gear_args.py to determine the structure of the inputs used throughout the remainder of the package.  

Stats_only_struct: Did you run the structural analysis already, but forgot to get the stats and can't find that analysis? You can check the stats_only_struct box on the Configuration tab, limit the stages to "PostFreeSurfer", and have the gear spit out those tables in a jiffy.

Logs: Error and execution logs from the HCP Pipelines are saved after each stage that attempted to run algorithms. These can be extra helpful, as `code: 134`, for example, often indicates an issue with a sub-command for the stage. The error log from HCP (encapsulated in the 'pipeline_logs.zip') will likely pinpoint the issue. The issue could be anything from a missing image, because a previous stage did not run, to a misspecified $SUBJ_DIR, which is most likely an issue for Flywheel to help troubleshoot.

## What went wrong?
- There are a couple of consistent issues to check before panicking that the gear is not going to run correctly.
1) Are the `task-label` and `run_label` fields spelled or enumerated correctly? The gear is looking to match the string following "task-" or "run-" from the BIDS naming verbatim. If there is a missing 0 in the run number or a misspelled task name, the gear will fail to resolve the scans you intended to analyze.
2) Are the fieldmaps designated to apply to the structural and/or functional images in the dicom header? The gear takes advantage of the BIDSLayout search algorithms from PyBIDS to find matching fmaps for the HCP pipelines. Failure to designate "IntendedFor" fields in the dicom are likely to lead to errors. One may be able to circumvent the dicom header issue by insuring that that "IntendedFor" fields are populated on the BIDS-curated project within Flywheel, but this alternative is not thoroughly tested.
3) Is the "debug" option set from the Configuration tab? Using that option may show you what is going wrong, but is necessary for Flywheel engineers to have a better idea of the issue, if helping troubleshoot.
4) Did you use "gear_save_or_error"? It would be awesome if you did! Not only will the pipeline_logs.zip be available, but there is a high chance of error messages being available in one place toward the end of your log and any successful analyses will have been recorded as output for the analysis.
5) If things look goofy after any particular stage, double check that the defaults from the configuration tab are what you intended. Maybe the unwarp direction for your structurals is set incorrectly. Though the gear attempts to glean information from the headers to confirm elements of the pipeline setup, it cannot guess everything. Please double-check that the initial settings are what you intended.


# HCP STRUCT
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the structural preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  Currently, this includes v4.0.1 release of PreFreeSurfer, FreeSurfer, and PostFreeSurfer pipelines, as well as generating some helpful QC images. The QC images are not necessary for the pipeline to complete properly and, therefore, are not required to run successfully for the gear to continue running. For more info on the pipelines, see [HCP Pipelines](https://github.com/Washington-University/Pipelines).

## Important notes
* T1w and T2w volumes should not have any online bias-correction (e.g.: no "Pre-scan Normalize" option on Siemens scanners). If on-scanner bias-correction was applied, it must be applied to **BOTH** T1w and T2w inputs.
* All MRI inputs (T1w, T2w, FieldMaps) must include BIDS-conformed DICOM metadata!
  ** Please make sure that the fieldmaps are appropriately specified in the header, as this algorithm relies on the BIDSLayout template to search for the intended fieldmap + corresponding images to be corrected.
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners. Though HCP has continued to develop the pipelines, these options are not currently available through this gear implementation.
* Readout distortion correction using B0 field maps (Field map "Option 1", below) is currently only available for data from Siemens scanners.  "TOPUP"-style correction (Field map "Option 2", below) should work for all data (but has not yet been tested). GE field maps are not supported as the algorithms are unavailable from HCP at this time.

## Required inputs
1. T1-weighted anatomical volume (eg: MPRAGE), <= 1mm spatial resolution
2. T2-weighted anatomical volume (eg: SPACE, FLAIR), <= 1mm spatial resolution
3. FreeSurfer license.txt file  (found in `$FREESURFER_HOME/license.txt`)

## Optional inputs
1. Field map for correcting readout distortion ("avgrdcmethod_struct")
    * Option 1: "typical" GRE B0 field map including magnitude and phase volumes
    * Option 2: a pair of spin echo with opposite phase-encode directions ("Positive" = R>>L or P>>A, and "Negative" = L>>R or A>>P) for "TOPUP"-style distortion estimation
    * **Note 1**: If readout distortion correction is performed, user **must** specify the correct "unwarp_dir_struct" config option.  For HCP scans (sagittal slices with A>>P phase-encoding), this should be "z", corresponding to readout in the F>>H direction.
    * Note 2: This effect is very small, at most 0.35mm in a few high-susceptibility areas (e.g., orbitofrontal)
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at `C:\MedCom\MriSiteData\GradientCoil\coeff.grad` for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)

## Configuration options
1. subject: Subject ID to use for outputs
2. reg_name: Surface registration type: either 'FS' (freesurfer) or 'MSMSulc' (HCP default). (See [FSL MSM](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/MSM) for details on MSMSulc)
3. brain_size: Brain size in mm (in Superior-Inferior axis), typically 150 (default) for adults
4. template_size: Voxel size of HCP anatomical template. Best if matches input. (Options = 0.7mm, 0.8mm (default), 1mm)
5. unwarp_dir_struct: Readout direction for structural scans ( 'x', 'x-', 'y', 'y-', 'z', 'z-' ). HCP default = 'z' (**Only used when providing fieldmaps to correct readout distortion**)

## Outputs
* `\<subject\>\_hcpstruct.zip`: Zipped output directory containing complete `MNINonLinear/`, `T1w/`, and `T2w/` folders.
  ** This zip file may be used as input for subsequent processing steps. In other words, once the FreeSurfer methods have been completed, you do not need to re-run the 
* `\<subject\>\_hcpstruct\_QC.*.png`: QC images for visual inspection of output quality (details to come...)
* Logs: Error and full run logs are available as "pipeline_logs.zip" on the analysis container


# HCP FUNC
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the functional preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  Currently, this includes v4.0-alpha release of fMRIVolume and fMRISurface, as well as generating some helpful QC images. For more info on the pipelines, see [HCP Pipelines](https://github.com/Washington-University/Pipelines).

## Important notes
* All MRI inputs (fMRI time series, FieldMaps) must include BIDS-conformed DICOM metadata!
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners.
* Readout distortion correction using B0 field maps (Field map "Option 1", below) is currently only available for data from Siemens scanners.  "TOPUP"-style correction (Field map "Option 2", below) should work for all data (but has not yet been tested).
* Analyses can be launched as stand-alone stages after structural analysis has been completed by selecting the hcpstruct.zip from the previous analysis.

## Required inputs
1. fMRI time series NiFTI
2. Field map for correcting readout distortion
    * Option 1: GRE = "typical" GRE B0 field map including magnitude and phase volumes
    * Option 2: SpinEchoFieldMap = a pair of spin echo with opposite phase-encode directions ("Positive" = R>>L or P>>A, and "Negative" = L>>R or A>>P) for "TOPUP"-style distortion estimation
3. StructZip output from the HCP-Struct gear (containing `T1w/`, `T2w/`, and `MNINonLinear/` folders), *if* running functional analyses independently.
4. FreeSurfer license.txt file  (found in `$FREESURFER_HOME/license.txt`)

## Optional inputs
1. fmri_scout: high-quality exemplar volume from fMRI time-series. If using Multi-Band for fMRI, and Single-Band reference volume is available, use SBRef. Otherwise, leave empty to first time series volume for registration.
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at `C:\MedCom\MriSiteData\GradientCoil\coeff.grad` for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)

## Configuration options
1. bias_correction_func: Bias-field estimation method. 'NONE' (default), 'SEBASED', or 'Legacy'. 'SEBASED'=Estimate from SpinEchoFieldMap (only possible with both Pos and Neg SpinEcho), 'Legacy'=Estimate from structural scans (only valid if structural collected in the same session, and without any subject movement)
2. mctype_func: Use 'MCFLIRT' (standard FSL moco) for most acquisitions.  'FLIRT'=custom algorithm used by HCP internally, but not recommended for public use
3. dof_func: Degrees of freedom for fMRI->Anat registration. 6 (default) = rigid body, when all data is from same scanner. 12 = full affine, recommended for 7T fMRI->3T anatomy
4. reg_name: Surface registration to use during CIFTI resampling: either 'FS' (freesurfer) or 'MSMSulc'. ('Empty'=gear uses reg_name from HCP-Structural)

## Outputs
* `\<subject\>\_\<fMRIName\>\_hcpfunc.zip`: Zipped output directory containing `\<fMRIName\>/` and `MNINonLinear/Results/\<fMRIName\>/` folders
* `\<subject\>\_\<fMRIName\>\_hcpfunc\_QC.*.png`: QC images for visual inspection of output quality (Distortion correction and registration to anatomy, details to come...)
* Logs (details to come...)

# HCP DIFF
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the diffusion preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  This includes correction for EPI distortion (using [FSL topup](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/topup/TopupUsersGuide)), correction for motion and eddy-current distortion (using [FSL eddy](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy)), and registration to subject anatomy. The *output of* this gear can serve as the *input* for diffusion modeling (eg: bedpostx) and tractography. For more info on the pipelines, see [HCP Pipelines](https://github.com/Washington-University/Pipelines).

## Important notes
* Diffusion time series must be provided in pairs with opposite phase-encoding.
* All MRI inputs must include BIDS-conformed DICOM metadata!
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners.

## Required inputs
1. Pair of diffusion scans (each including NiFTI+bvec+bval) with identical acquisitions but opposite phase-encoding (R>>L + L>>R, *or* P>>A + A>>P)
3. StructZip output from the HCP-Struct gear (containing `T1w/`, `T2w/`, and `MNINonLinear/` folders), if analyzing diffusion separately from structural.
4. FreeSurfer license.txt file  (found in `$FREESURFER_HOME/license.txt`)

## Optional inputs
1. Additional diffusion pairs *from the same session* (DWIPositiveData2 + DWINegativeData2, etc...)
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at `C:\MedCom\MriSiteData\GradientCoil\coeff.grad` for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)

## Outputs
* `\<subject\>\_\<DWIName\>\_hcpdiff.zip`: Zipped output directory containing `\<subject\>/<DWIName\>/` and `\<subject\>/T1w/<DWIName\>/` folders
* `\<subject\>\_\<DWIName\>\_hcpdiff\_QC.*.png`: QC images for visual inspection of output quality (details to come...)
* Logs (details to come...)

## Gear Release Notes
The latest iteration of the hcp gears use a common docker base image to consolidate both library installations and common functionality across gears.  See [HCP Base Docker Image](https://github.com/flywheel-apps/hcp-base) for details.

## Important HCP Pipeline links
* [HCP Pipelines](https://github.com/Washington-University/Pipelines)
* [HCP Pipelines FAQ](https://github.com/Washington-University/Pipelines/wiki/FAQ)
* [HCP Pipelines v3.4.0 release notes](https://github.com/Washington-University/Pipelines/wiki/v3.4.0-Release-Notes,-Installation,-and-Usage)
