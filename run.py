#!/usr/bin/env python3
import os, os.path as op
import json
import subprocess as sp
import copy
import shutil

import flywheel
from utils.custom_logger import get_custom_logger, log_config
from utils.args import PreFreeSurfer, FreeSurfer, PostFreeSurfer
from utils.args import hcpstruct_qc_scenes, hcpstruct_qc_mosaic
from utils.args import PostProcessing
from utils import results

if __name__ == '__main__':
    # Get the Gear Context
    context = flywheel.GearContext()
    # Activate custom logger
    context.log = get_custom_logger('[flywheel/hcp-struct]')
    # Set up Custom Dicionary to host user variables
    context.custom_dict={}
    context.custom_dict['SCRIPT_DIR']    = '/tmp/scripts'
    context.custom_dict['SCENE_DIR']     = '/tmp/scenes'
    context.custom_dict['FreeSurfer_Version'] = '5.3.0'
    # Instantiate Environment Variables
    # This will always be '/tmp/gear_environ.json' with these 
    # environments defined in the Dockerfile and exported from there.
    with open('/tmp/gear_environ.json', 'r') as f:
        environ = json.load(f)

    context.custom_dict['environ'] = environ
    # Create a 'dry run' flag for debugging
    context.custom_dict['dry-run'] = False
     
    ###########################################################################
    # Pipelines common commands
    QUEUE = ""
    LogFileDirFull = op.join(context.work_dir,'logs')
    os.makedirs(LogFileDirFull, exist_ok=True)
    FSLSUBOPTIONS = "-l "+ LogFileDirFull

    command_common=[op.join(environ['FSLDIR'],'bin','fsl_sub'),
                   QUEUE, FSLSUBOPTIONS]
    
    context.custom_dict['command_common'] = command_common

    
    ###########################################################################
    # Build and Validate parameters for all stages of the pipeline before
    # attempting to execute. Correct parameters or gracefully recover where
    # possible.
    ###########################################################################
    # Report on Inputs and configuration parameters to the log
    log_config(context)
    # Build and Validate Parameters for the PreFreeSurferPipeline.sh 
    try:
        PreFreeSurfer.build(context)
        PreFreeSurfer.validate(context)
    except Exception as e:
        context.log.fatal(e,)
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
        context.log.fatal(e)
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
        context.log.fatal(e)
        context.log.fatal(
            'Validating Parameters for the PostFreeSurferPipeline Failed!'
        )
        os.sys.exit(1)        

    ###########################################################################
    # Run PreFreeSurferPipeline.sh from subprocess.run
    try:
        PreFreeSurfer.execute(context)
    except Exception as e:
        context.log.fatal(e,)
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
        context.log.fatal(e)
        context.log.fatal('The FreeSurferPipeline Failed.')
        if context.config['save-on-error']:
            results.cleanup(context)
        os.sys.exit(1)

    ###########################################################################
    # Run PostFreeSurferPipeline.sh from subprocess.run
    try:
        PostFreeSurfer.execute(context)
    except Exception as e:
        context.log.fatal(e)
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
        context.log.fatal(e)
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
        context.log.fatal(e,)
        context.log.fatal('HCP Structural QC Images has failed!')
        if context.config['save-on-error']:
            results.cleanup(context)
        exit(1)

    ###########################################################################
    # Clean-up and output prep
    results.cleanup(context)
    os.sys.exit(0)
