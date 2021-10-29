##0.2.0_4.3.0
### Fixes
- SSL cert upgraded
### Enhancements
- Logs are produced and saved for all stages run in the analysis
- Analyses can reliably be continued using previous, structural processing by indicating which hcpstruct.zip to use.
- Test suite has been added to cover about 75% of the code.
- Stats_only_struct option allows users to (re)run stats for structural analyses. (Quick summaries, needed for pubs)
### Other changes
- Large-scale refactor of variable names for internal consistency.
### Documentation
- Readme has been revisited and edited.

##v0.0.1_4.3.0
###Fixes
- HCP-base image calls the proper workbench URL for download
### Enhancements
- All major processing steps can be accessed from this single gear.
- The BIDS files are automatically populated from the directory structure.
