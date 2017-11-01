# flywheel/hcp-struct
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that runs the structural preprocessing steps of the [Human Connectome Project](http://www.humanconnectome.org) Minimal Preprocessing Pipeline (MPP) described in [Glasser et al. 2013](http://www.ncbi.nlm.nih.gov/pubmed/23668970).  Currently, this includes v4.0-alpha release of PreFreeSurfer, FreeSurfer, and PostFreeSurfer pipelines, as well as generating some helpful QC images.

## Important Notes
* T1w and T2w volumes should not have any online bias-correction (e.g.: no "Pre-scan Normalize" option on Siemens scanners). If on-scanner bias-correction was applied, it must be applied to **BOTH** T1w and T2w inputs.
* All MRI inputs (T1w, T2w, FieldMaps) must include BIDS-conformed DICOM metadata!
* Gradient nonlinearity correction (using coefficient file) is currently only available for data from Siemens scanners.
* Readout distortion correction using B0 field maps (Field map "Option 1", below) is currently only available for data from Siemens scanners.  "TOPUP"-style correction (Field map "Option 2", below) should work for all data (but has not yet been tested).

## Required inputs
1. T1-weighted anatomical volume (eg: MPRAGE), <= 1mm spatial resolution
2. T2-weighted anatomical volume (eg: SPACE, FLAIR), <= 1mm spatial resolution

## Optional inputs
1. Field map for correcting readout distortion
    * Option 1: "typical" GRE B0 field map including magnitude and phase volumes
    * Option 2: a pair of spin echo with opposite phase-encode directions ("Positive" = R>>L or P>>A, and "Negative" = L>>R or A>>P) for "TOPUP"-style distortion estimation
    * **Note 1**: If readout distortion correction is performed, user **must** specify the correct "StructualUnwarpDirection" config option.  For HCP scans (sagittal slices with A>>P phase-encoding), this should be "z", corresponding to readout in the F>>H direction.
    * Note 2: This effect is very small, at most 0.35mm in a few high-susceptibility areas (e.g., orbitofrontal)
2. Gradient nonlinearity coefficients copied from scanner. See [FAQ 8. What is gradient nonlinearity correction?](https://github.com/Washington-University/Pipelines/wiki/FAQ#8-what-is-gradient-nonlinearity-correction)
    * If needed, this file can be obtained from the console at <code>C:\MedCom\MriSiteData\GradientCoil\coeff.grad</code> for Siemens scanners
    * Note: This effect is significant for HCP data collected on custom Siemens "ConnectomS" scanner, and for 7T scanners.  It is relatively minor for production 3T scanners (Siemens Trio, Prisma, etc.)
3. FreeSurfer license.txt file  (found in <code>$FREESURFER_HOME/license.txt</code>)

## Outputs
* <code>\<subject\>_hcpstruct.zip</code>: Zipped output directory containing complete MNINonLinear/ T1w/ and T2w/ folders
* <code>\<subject\>_hcpstruct_QC.*.png</code>: QC images for visual inspection of output quality (details to come...)
* Logs (details to come...)

## Important HCP Pipeline links
* [HCP Pipelines](https://github.com/Washington-University/Pipelines)
* [HCP Pipelines FAQ](https://github.com/Washington-University/Pipelines/wiki/FAQ)
* [HCP Pipelines v3.4.0 release notes](https://github.com/Washington-University/Pipelines/wiki/v3.4.0-Release-Notes,-Installation,-and-Usage)
