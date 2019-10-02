import os, os.path as op
import re
import subprocess as sp
from collections import OrderedDict 
from .Common import BuildCommandList

def build(context):
    SCENE_DIR = context.custom_dict['SCENE_DIR']
    params = OrderedDict()
    params['qc_scene_template'] = op.join(SCENE_DIR,
        'TEMPLATE.hcpstruct_QC.very_inflated.164k_fs_LR.scene')
    params['qc_scene_file'] = op.join(
        context.work_dir,context.config['Subject'],
        'MNINonLinear', context.config['Subject'] + \
        '.hcpstruct_QC.164k_fs_LR.scene')
    params['qc_subject'] = context.config['Subject']
    params['qc_scene_root']=op.join(context.work_dir,context.config['Subject'])

    params['qc_outputdir']=context.work_dir 
   

    params['qc_image_root']=op.join(context.work_dir,
                            context.config['Subject']+ \
                            '.hcpstruct_QC.' + \
                            'inflated_')
    # qc image size
    params['qc_image_params']="1440 900" 
    context.custom_dict['params']=params

def execute(context):
    environ = context.custom_dict['environ']
    SCRIPT_DIR = context.custom_dict['SCRIPT_DIR']
    os.makedirs(context.custom_dict['params']['qc_outputdir'],exist_ok=True)
    context.custom_dict['params'].pop('qc_outputdir')
    command =[op.join(SCRIPT_DIR,'hcpstruct_qc_scenes.sh')]
    for key in context.custom_dict['params'].keys():
        command.append(context.custom_dict['params'][key])
    # command.append('>')
    # command.append(op.join(context.work_dir,'logs','structuralqc.log'))
    context.log.info('HCP-Struct QC Scenes command: \n' + ' '.join(command) + \
                     '\n\n')
    if not context.custom_dict['dry-run']:
        result = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE,
                        universal_newlines=True, env=environ)
        stdout, stderr = result.communicate()
        context.log.info(result.returncode)
        context.log.info(stdout)

        if result.returncode != 0:
            context.log.error('The command:\n ' +
                              ' '.join(command) +
                              '\nfailed. See log for debugging.')
            raise Exception(stderr)
