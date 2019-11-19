"""
This is a module with specific functions for the HCP Functional Pipeline
"""
import subprocess as sp
import os, os.path as op

def get_freesurfer_version(context):
    """
    This function returns the version of freesurfer used.
    This is need to determine which HCP/FreeSurfer.sh to run.
    """
    environ = context.gear_dict['environ']
    command = ['freesurfer --version']
    result = sp.Popen(
        command, 
        stdout=sp.PIPE, 
        stderr=sp.PIPE, 
        universal_newlines=True, 
        shell=True,
        env=environ
    )
    stdout, _ = result.communicate()
    start = stdout.find('-v') + 2
    end = stdout.find('-',start)
    version = stdout[start:end]
    return version

def configs_to_export(context):
    """
    Export HCP Functional Pipeline configuration into the Subject directory
    Return the config and filename
    """
    config = {}
    hcpstruct_config={'config': config}
    for key in [
        'RegName',
        'Subject',
        'GrayordinatesResolution',
        'GrayordinatesTemplate',
        'HighResMesh',
        'LowResMesh'
    ]:
        if key in context.config.keys():
            config[key]=context.config[key]

    hcpstruct_config_filename = op.join(
        context.work_dir,
        context.config['Subject'],
        '{}_hcpstruct_config.json'.format(context.config['Subject'])
    )
    
    return hcpstruct_config, hcpstruct_config_filename