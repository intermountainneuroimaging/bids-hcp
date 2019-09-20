import os, os.path as op
import json
import subprocess as sp
import shutil
import pandas as pd

def save_hcpstruct_config(context):
    # Add current gear config.json to output for reference in subsequent gears
    # - For now, don't copy full input json since it might contain identifiers from DICOM etc
    # - add/update .config.RegName since it might not have been included in config (pre-MSM availability)
    # - add/update .config.Subject since it might later be pulled from other session metadata
    # - This jq call does the value replacement, then selects just .config but stores it back into a
    #    new element called ".config" so the new file can be read as though it was flywheel config.json
    hcpstruct_config={}
    for key in [
        'RegName',
        'Subject',
        'GrayordinatesResolution',
        'GrayordinatesTemplate',
        'HighResMesh',
        'LowResMesh'
    ]:
        if key in context.config.keys():
            hcpstruct_config[key]=context.config[key]

    with open(op.join(context.work_dir,context.config['Subject'],
            context.config['Subject']+'_hcpstruct_config.json'),'w') as f:
        json.dump(hcpstruct_config,f)

def preserve_whitelist_files(context):
    for fl in context.custom_dict['whitelist']:
        if not context.custom_dict['dry-run']:
            context.log.info('Copying file to output: {}'.format(fl))
            shutil.copy(fl,context.output_dir)
            

def zip_hcpstruct_output(context):
    environ = context.custom_dict['environ']
    outputzipname=context.config['Subject']+'_hcpstruct.zip'
    context.log.info('Zipping output file {}'.format(outputzipname))
    os.chdir(context.work_dir)
    try:
        os.remove(op.join(context.output_dir,logzipname))
    except:
        pass
    # To use bash redirects (e.g. >,>>,&>,..), subprocess requires a single 
    # string and the shell=True
    command = ['zip','-r', op.join(context.output_dir,outputzipname),
               context.config['Subject'], '>',
               op.join(context.output_dir,outputzipname+'.log')]
    command = ' '.join(command)
    context.log.info("The ZIP command is:\n"+command)
    if not context.custom_dict['dry-run']:
        p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE, shell=True,
                    universal_newlines=True, env=environ)
        # Wait for Popen call to finish
        p.communicate()

def zip_pipeline_logs(context):
    # zip pipeline logs
    environ = context.custom_dict['environ']
    logzipname='pipeline_logs.zip'
    context.log.info('Zipping pipeline logs to {}'.format(logzipname))
    os.chdir(context.work_dir)
    try:
        os.remove(op.join(context.output_dir,logzipname))
    except:
        pass
    # To use bash redirects (e.g. >,>>,&>,..), subprocess requires a single 
    # string and the shell=True
    command=['zip','-r', op.join(context.output_dir,logzipname),
             op.join(context.work_dir,'logs'), '>',
             op.join(context.output_dir,logzipname+'.log')]
    command = ' '.join(command)
    context.log.info("The ZIP command is:\n"+command)
    if not context.custom_dict['dry-run']:         
        p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE, shell=True,
                    universal_newlines=True, env=environ)
        # Wait for Popen call to finish
        p.communicate()

def cleanup(context):
    # Move all images to output directory
    try:
        command = 'cp '+ context.work_dir+'/*.png ' + context.output_dir + '/'
        p = sp.Popen(
            command,
            shell=True
        )
        p.communicate()
    except:
        context.log.error('There are no images to save.')
    save_hcpstruct_config(context)
    zip_hcpstruct_output(context)
    zip_pipeline_logs(context)
    preserve_whitelist_files(context)
    # Write Metadata to file
    if 'metadata' in context.custom_dict.keys():
        info = context.custom_dict['metadata']['analysis']['info']
        context.log.info(info) # TODO: Remove
        context.log.info(context.custom_dict['metadata']) # TODO: Remove
        context.update_container_metadata('session',info = info)
        context.write_metadata()
        if op.exists(op.join(context.output_dir,'.metadata.json')):
            context.log.info(
             '{} exists'.format(op.join(context.output_dir,'.metadata.json'))
            )
            context.log.info(open(op.join(context.output_dir,'.metadata.json'),'r').read())
        elif op.exists(op.join(context.work_dir,'.metadata.json')):
            context.log.info(
                '{} exists'.format(op.join(context.work_dir,'.metadata.json'))
            )
        else:
            context.log.warning('Could not find .metadata.json!!!')
    # List final directory to log
    context.log.info('Final output directory listing: \n')
    os.chdir(context.output_dir)
    duResults = sp.Popen('du -hs *',shell=True,stdout=sp.PIPE, stderr=sp.PIPE,
                universal_newlines=True)
    stdout, _ = duResults.communicate()
    context.log.info('\n' + stdout)           