[![Docker Pulls](https://img.shields.io/docker/pulls/flywheel/hcp-struct.svg)](https://hub.docker.com/r/flywheel/hcp-struct/)
[![Docker Stars](https://img.shields.io/docker/stars/flywheel/hcp-struct.svg)](https://hub.docker.com/r/flywheel/hcp-struct/)
#OVERVIEW


# HCP STRUCT
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the structural preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  Currently, this includes v4.0.1 release of PreFreeSurfer, FreeSurfer, and PostFreeSurfer pipelines, as well as generating some helpful QC images. For more info on the pipelines, see [HCP Pipelines](https://github.com/Washington-University/Pipelines).

## Important notes
* T1w and T2w volumes should not have any online bias-correction (e.g.: no "Pre-scan Normalize" option on Siemens scanners). If on-scanner bias-correction was applied, it must be applied to **BOTH** T1w and T2w inputs.
* All MRI inputs (T1w, T2w, FieldMaps) must include BIDS-conformed DICOM metadata!
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners.
* Readout distortion correction using B0 field maps (Field map "Option 1", below) is currently only available for data from Siemens scanners.  "TOPUP"-style correction (Field map "Option 2", below) should work for all data (but has not yet been tested).

## Required inputs
1. T1-weighted anatomical volume (eg: MPRAGE), <= 1mm spatial resolution
2. T2-weighted anatomical volume (eg: SPACE, FLAIR), <= 1mm spatial resolution
3. FreeSurfer license.txt file  (found in <code>$FREESURFER_HOME/license.txt</code>)

## Optional inputs
1. Field map for correcting readout distortion
    * Option 1: "typical" GRE B0 field map including magnitude and phase volumes
    * Option 2: a pair of spin echo with opposite phase-encode directions ("Positive" = R>>L or P>>A, and "Negative" = L>>R or A>>P) for "TOPUP"-style distortion estimation
    * **Note 1**: If readout distortion correction is performed, user **must** specify the correct "StructualUnwarpDirection" config option.  For HCP scans (sagittal slices with A>>P phase-encoding), this should be "z", corresponding to readout in the F>>H direction.
    * Note 2: This effect is very small, at most 0.35mm in a few high-susceptibility areas (e.g., orbitofrontal)
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at <code>C:\MedCom\MriSiteData\GradientCoil\coeff.grad</code> for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)

## Configuration options
1. Subject: Subject ID to use for outputs
2. RegName: Surface registration type: either 'FS' (freesurfer) or 'MSMSulc' (HCP default). (See [FSL MSM](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/MSM) for details on MSMSulc)
3. BrainSize: Brain size in mm (in Superior-Inferior axis), typically 150 (default) for adults
4. TemplateSize: Voxel size of HCP anatomical template. Best if matches input. (Options = 0.7mm, 0.8mm (default), 1mm)
5. StructuralUnwarpDirection: Readout direction for structural scans ( 'x', 'x-', 'y', 'y-', 'z', 'z-' ). HCP default = 'z' (**Only used when providing fieldmaps to correct readout distortion**)

## Outputs
* <code>\<subject\>\_hcpstruct.zip</code>: Zipped output directory containing complete <code>MNINonLinear/</code>, <code>T1w/</code>, and <code>T2w/</code> folders.
* <code>\<subject\>\_hcpstruct\_QC.*.png</code>: QC images for visual inspection of output quality (details to come...)
* Logs (details to come...)


# HCP FUNC
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the functional preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  Currently, this includes v4.0-alpha release of fMRIVolume and fMRISurface, as well as generating some helpful QC images. For more info on the pipelines, see [HCP Pipelines](https://github.com/Washington-University/Pipelines).

## Important notes
* All MRI inputs (fMRI time series, FieldMaps) must include BIDS-conformed DICOM metadata!
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners.
* Readout distortion correction using B0 field maps (Field map "Option 1", below) is currently only available for data from Siemens scanners.  "TOPUP"-style correction (Field map "Option 2", below) should work for all data (but has not yet been tested).

## Required inputs
1. fMRI time series NiFTI
2. Field map for correcting readout distortion
    * Option 1: GRE = "typical" GRE B0 field map including magnitude and phase volumes
    * Option 2: SpinEchoFieldMap = a pair of spin echo with opposite phase-encode directions ("Positive" = R>>L or P>>A, and "Negative" = L>>R or A>>P) for "TOPUP"-style distortion estimation
3. StructZip output from the HCP-Struct gear (containing <code>T1w/</code>, <code>T2w/</code>, and <code>MNINonLinear/</code> folders)
4. FreeSurfer license.txt file  (found in <code>$FREESURFER_HOME/license.txt</code>)

## Optional inputs
1. fMRIScout: high-quality exemplar volume from fMRI time-series. If using Multi-Band for fMRI, and Single-Band reference volume is available, use SBRef. Otherwise, leave empty to first time series volume for registration.
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at <code>C:\MedCom\MriSiteData\GradientCoil\coeff.grad</code> for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)

## Configuration options
1. fMRIName: Output name for preprocessed data (default = rfMRI\_REST)
2. BiasCorrection: Bias-field estimation method. 'NONE' (default), 'SEBased', or 'Legacy'. 'SEBased'=Estimate from SpinEchoFieldMap (only possible with both Pos and Neg SpinEcho), 'Legacy'=Estimate from structural scans (only valid if structural collected in the same session, and without any subject movement)
3. MotionCorrection: Use 'MCFLIRT' (standard FSL moco) for most acquisitions.  'FLIRT'=custom algorithm used by HCP internally, but not recommended for public use
4. AnatomyRegDOF: Degrees of freedom for fMRI->Anat registration. 6 (default) = rigid body, when all data is from same scanner. 12 = full affine, recommended for 7T fMRI->3T anatomy
5. RegName: Surface registration to use during CIFTI resampling: either 'FS' (freesurfer) or 'MSMSulc'. ('Empty'=gear uses RegName from HCP-Structural)

## Outputs
* <code>\<subject\>\_\<fMRIName\>\_hcpfunc.zip</code>: Zipped output directory containing <code>\<fMRIName\>/</code> and <code>MNINonLinear/Results/\<fMRIName\>/</code> folders
* <code>\<subject\>\_\<fMRIName\>\_hcpfunc\_QC.*.png</code>: QC images for visual inspection of output quality (Distortion correction and registration to anatomy, details to come...)
* Logs (details to come...)

# HCP DIFF
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the diffusion preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  This includes correction for EPI distortion (using [FSL topup](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/topup/TopupUsersGuide)), correction for motion and eddy-current distortion (using [FSL eddy](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy)), and registration to subject anatomy. The *output of* this gear can serve as the *input* for diffusion modeling (eg: bedpostx) and tractography. For more info on the pipelines, see [HCP Pipelines](https://github.com/Washington-University/Pipelines).

## Important notes
* Diffusion time series must be provided in pairs with opposite phase-encoding.
* All MRI inputs must include BIDS-conformed DICOM metadata!
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners.

## Required inputs
1. Pair of diffusion scans (each including NiFTI+bvec+bval) with identical acquisitions but opposite phase-encoding (R>>L + L>>R, *or* P>>A + A>>P)
3. StructZip output from the HCP-Struct gear (containing <code>T1w/</code>, <code>T2w/</code>, and <code>MNINonLinear/</code> folders)
4. FreeSurfer license.txt file  (found in <code>$FREESURFER_HOME/license.txt</code>)

## Optional inputs
1. Additional diffusion pairs *from the same session* (DWIPositiveData2 + DWINegativeData2, etc...)
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at <code>C:\MedCom\MriSiteData\GradientCoil\coeff.grad</code> for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)

## Outputs
* <code>\<subject\>\_\<DWIName\>\_hcpdiff.zip</code>: Zipped output directory containing <code>\<subject\>/<DWIName\>/</code> and <code>\<subject\>/T1w/<DWIName\>/</code> folders
* <code>\<subject\>\_\<DWIName\>\_hcpdiff\_QC.*.png</code>: QC images for visual inspection of output quality (details to come...)
* Logs (details to come...)

## Gear Release Notes
The latest iteration of the hcp gears use a common docker base image to consolidate both library installations and common functionality across gears.  See [HCP Base Docker Image](https://github.com/flywheel-apps/hcp-base) for details.

## Important HCP Pipeline links
* [HCP Pipelines](https://github.com/Washington-University/Pipelines)
* [HCP Pipelines FAQ](https://github.com/Washington-University/Pipelines/wiki/FAQ)
* [HCP Pipelines v3.4.0 release notes](https://github.com/Washington-University/Pipelines/wiki/v3.4.0-Release-Notes,-Installation,-and-Usage)
