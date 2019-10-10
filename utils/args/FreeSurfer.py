import os, os.path as op
import subprocess as sp
from collections import OrderedDict
from .Common import BuildCommandList, exec_command

def build(context):
    config = context.config
    params = OrderedDict()
    params['subject'] = config['Subject']
    # Location to Put FreeSurfer Subject's Folder
    params['subjectDIR'] = op.join(context.work_dir, config['Subject'], 'T1w')
    # T1w FreeSurfer Input (Full Resolution)
    params['t1'] = op.join(context.work_dir, config['Subject'], 'T1w',
                           'T1w_acpc_dc_restore.nii.gz')
    # T1w FreeSurfer Input (Full Resolution)
    params['t1brain'] = op.join(context.work_dir, config['Subject'], 'T1w',
                                'T1w_acpc_dc_restore_brain.nii.gz')
    # T2w FreeSurfer Input (Full Resolution)
    params['t2'] = op.join(context.work_dir, config['Subject'], 'T1w',
                           'T2w_acpc_dc_restore.nii.gz')
    params['printcom'] = " "
    context.custom_dict['FS-params'] = params

def validate(context):
    params = context.custom_dict['FS-params']
    # Make sure these exists where expected
    not_found = []
    for param in ['subjectDIR', 't1', 't1brain', 't2']:
        if param not in params.keys():
            raise Exception("FreeSurfer Parameter Building Failed.")
        if not op.exists(params[param]):
            not_found.append(params[param])
    if (len(not_found) > 0) and (not context.custom_dict['dry-run']):
        raise Exception(
            "The following files where not found: " + ','.join(not_found))

def execute(context):
    environ = context.custom_dict['environ']
    command = []
    command.extend(context.custom_dict['command_common'])
    # HCP v4.0.0 has FreeSurferPipeline scripts for both Freesurfer 5.3.0 and
    # Freesurfer 6.0.2
    # For FreeSurfer 5.3.0: FreeSurferPipeline-v5.3.0-HCP.sh
    # For FreeSurfer 6.0.1: FreeSurferPipeline.sh
    command.append(
        op.join(environ['HCPPIPEDIR'],'FreeSurfer',
        'FreeSurferPipeline-v5.3.0-HCP.sh')
        )
    command = BuildCommandList(command,context.custom_dict['FS-params'])
    stdout_msg = 'FreeSurfer logs (stdout, stderr) will be available in the ' + \
                 'file "pipeline_logs.zip" upon completion.'

    context.log.info('FreeSurfer command: \n')
    exec_command(context,command,stdout_msg = stdout_msg)