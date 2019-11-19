"""
This module elevates "whitelisted" files to the toplevel of this gear's output
directory.  This is as specified in 
https://github.com/scitran-apps/freesurfer-recon-all/blob/master/bin/run#L206-L317.
However, what is requested in the volume and area information of the FS output
rather than the registered and segmented volumes and surfaces (L296-L317).
part of the hcp-struct gear
"""
import os, os.path as op
import subprocess as sp
import pandas as pd
from .common import exec_command

def build(context):
    # TODO: Is this in gear_preliminaries?
    context.gear_dict['whitelist'] = []
    context.gear_dict['metadata'] = {}

def validate(context):
    pass

def set_metadata_from_csv(context,csv_file):
    info = context.gear_dict['metadata']['analysis']['info']
    if op.exists(csv_file):
        df = pd.read_csv(csv_file,sep=',')
        columns = df.columns
        # First column is the name of the csv
        # To avoid name collisions, organize these by seg_title
        seg_title = columns[0].replace('.','_')
        info[seg_title] = {}
        # All but the first column which is subject_id
        for col in columns[1:]:
            info[seg_title][col] = df[col][0]

def process_aseg_csv(context):
    whitelist = context.gear_dict['whitelist']
    config = context.config
    # Check for the presence of keys.
    metadata = context.gear_dict['metadata']
    if not 'analysis' in metadata.keys():
        metadata['analysis'] = {}

    if not 'info' in metadata['analysis'].keys():
        metadata['analysis']['info'] = {}

    tablefile = \
        op.join(
            context.work_dir,config['Subject']+'_aseg_stats_vol_mm3.csv'
        )
    command = [
        'asegstats2table', 
        '-s', config['Subject'],
        '--delimiter', 'comma',
        '--tablefile=' + tablefile
    ]
    exec_command(context,command)
    whitelist.append(tablefile)
    set_metadata_from_csv(context,tablefile)

    for hemi in ['lh', 'rh']:
        for parc in ['aparc.a2009s', 'aparc']:
            tablefile = \
                op.join(
                    context.work_dir,
                    '{}_{}_{}_stats_area_mm2.csv'.format(
                        config['Subject'],
                        hemi,
                        parc
                    )
                )
            command = [
                'aparcstats2table', 
                '-s', config['Subject'],
                '--hemi=' + hemi,
                '--delimiter=comma',
                '--parc=' + parc,
                '--tablefile=' + tablefile                    
            ]
            exec_command(context,command)
            whitelist.append(tablefile)
            set_metadata_from_csv(context,tablefile) 
            
def execute(context):
    config = context.config
    # The commands below only work with this 
    # symbolic link in place
    subject = config['Subject']
    command = [
        'ln', 
        '-s', 
        '-f', 
        '{}/{}/T1w/{}'.format(context.work_dir,subject,subject), 
        '/opt/freesurfer/subjects/'
    ]
    exec_command(context,command)

    # Process segmentation data to csv and process to metadata
    if config['aseg_csv']:
        context.log.info('Exporting stats files csv...')
        process_aseg_csv(context)