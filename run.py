#!/usr/bin/env python3
import os, os.path as op
import json
import subprocess as sp
import copy
import shutil

import flywheel
from utils.custom_logger import get_custom_logger
from utils.args import PreFreeSurfer, FreeSurfer, PostFreeSurfer
from utils.args import hcpstruct_qc_scenes, hcpstruct_qc_mosaic
from utils.args import PostProcessing
from utils import results, gear_preliminaries
from utils.struct_utils import get_freesurfer_version

if __name__ == '__main__':
    # Preamble: take care of all gear-typical activities.
    context = flywheel.GearContext()
    context.gear_dict = {}
    # Initialize all hcp-gear variables.
    gear_preliminaries.initialize_gear(context)
    context.log_config()

    # Validate gear configuration against gear manifest
    try:
        gear_preliminaries.validate_config_against_manifest(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            'Please make the prescribed corrections and try again.'
        )
        os.sys.exit(1)

    # Can I automate this? Do I want to?
    context.gear_dict['FreeSurfer_Version'] = get_freesurfer_version(context)

     
    ###########################################################################
    # Pipelines common commands
    # QUEUE works differently in FSL 6.0.1..we are not using it.
    QUEUE = "-q "
    LogFileDirFull = op.join(context.work_dir,'logs')
    os.makedirs(LogFileDirFull, exist_ok=True)
    FSLSUBOPTIONS = "-l "+ LogFileDirFull
    environ = context.gear_dict['environ']
    command_common=[op.join(environ['FSLDIR'],'bin','fsl_sub'), FSLSUBOPTIONS]
    
    context.gear_dict['command_common'] = command_common

    
    ###########################################################################
    # Build and Validate parameters for all stages of the pipeline before
    # attempting to execute. Correct parameters or gracefully recover where
    # possible.
    ###########################################################################
    # Ensure the subject_id is set in a valid manner (api or config)
    try:
        gear_preliminaries.set_subject(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            'The Subject ID is not valid. Examine and try again.',
        )
        os.sys.exit(1)

    # Build and Validate Parameters for the PreFreeSurferPipeline.sh 
    try:
        PreFreeSurfer.build(context)
        PreFreeSurfer.validate(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            'Validating Parameters for the PreFreeSurferPipeline Failed.',
        )
        os.sys.exit(1)

    ###########################################################################
    # Build and Validate Parameters for the FreeSurferPipeline.sh
    try:
        FreeSurfer.build(context)
        # These parameters need to be validated after the PreFS run
        # No user-submitted parameters to validate at this level
        # FreeSurfer.validate(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            'Validating Parameters for the FreeSurferPipeline Failed.'
        )
        os.sys.exit(1)

    ###########################################################################
    # Build and Validate Parameters for the PostFreeSurferPipeline.sh
    try:
        PostFreeSurfer.build(context)
        PostFreeSurfer.validate(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            'Validating Parameters for the PostFreeSurferPipeline Failed!'
        )
        os.sys.exit(1)        

    ###########################################################################
    # Run PreFreeSurferPipeline.sh from subprocess.run
    try:
        PreFreeSurfer.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal(
            'The PreFreeSurferPipeline Failed.',
        )
        if context.config['save-on-error']:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Run FreeSurferPipeline.sh from subprocess.run
    try:
        FreeSurfer.validate(context)
        FreeSurfer.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal('The FreeSurferPipeline Failed.')
        if context.config['save-on-error']:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Run PostFreeSurferPipeline.sh from subprocess.run
    try:
        PostFreeSurfer.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal('The PostFreeSurferPipeline Failed!')
        if context.config['save-on-error']:
            results.cleanup(context)
        os.sys.exit(1)  

    ###########################################################################
    # Run PostProcessing for "whitelisted" files
    #  - "whitelisted" files being copied direclty to ./output/ rather than
    #    being compressed into the result zip file.
    try:
        PostProcessing.build(context)
        PostProcessing.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal('The Post Processing Failed!')
        if context.config['save-on-error']:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Generate HCPStructural QC Images
    try:
        hcpstruct_qc_scenes.build(context)
        hcpstruct_qc_scenes.execute(context)

        hcpstruct_qc_mosaic.build(context)
        hcpstruct_qc_mosaic.execute(context)
    except Exception as e:
        context.log.exception(e)
        context.log.fatal('HCP Structural QC Images has failed!')
        if context.config['save-on-error']:
            results.cleanup(context)
        exit(1)

    ###########################################################################
    # Clean-up and output prep
    results.cleanup(context)
    os.sys.exit(0)
