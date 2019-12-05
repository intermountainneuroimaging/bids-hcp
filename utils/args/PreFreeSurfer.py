"""
Builds, validates, and excecutes parameters for the HCP script 
/opt/HCP-Pipelines/PreFreeSurfer/PreFreeSurferPipeline.sh
part of the hcp-struct gear
"""
import os, os.path as op
import re
import subprocess as sp
import shutil
from tr import tr
from collections import OrderedDict
from .common import build_command_list, exec_command

def build(context):
    environ = context.gear_dict['environ']
    config = context.config
    inputs = context._invocation['inputs']

    params = OrderedDict()

    # Check for all required inputs. Necessary for API calls
    # TODO: this should be taken care of in gear_preliminaries
    missing=[]
    for req in ['T1','T2']:
        if not req in inputs.keys():
            missing.append(req)
    if len(missing)>0:
        raise Exception(
        'Please provide the required input file(s), {}!'.format(missing)
        )

    params['path'] = context.work_dir
    params['subject'] = config['Subject']
    params['t1'] = context.get_input_path('T1')
    params['t2'] = context.get_input_path('T2')

    # Pre-Fill certain parameters with "NONE"
    None_Params=[
                'fmapmag','fmapphase',
                'fmapgeneralelectric',
                'SEPhaseNeg','SEPhasePos','seechospacing','seunwarpdir',
                'echodiff','t1samplespacing','t2samplespacing',
                'gdcoeffs','avgrdcmethod','topupconfig'
                ]
    # the parameter "--bfsigma" is not accounted for
    for p in None_Params:
        params[p] = "NONE"

    if "DwellTime" in inputs["T1"]["object"]["info"].keys():
        dwell_time = inputs["T1"]["object"]["info"]["DwellTime"]
        # format dwell_time to 15 places
        params['t1samplespacing'] = format(dwell_time,'.15f')
    if "DwellTime" in inputs["T2"]["object"]["info"].keys():
        dwell_time = inputs["T2"]["object"]["info"]["DwellTime"]
        # format dwell_time to 15 places
        params['t2samplespacing'] = format(dwell_time,'.15f')

    # HCP PIPE DIR Templates
    # MNI0.7mm template
    params['t1template'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T1_' + config['TemplateSize'] + '.nii.gz'
    params['t1template2mm'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T1_2mm.nii.gz'  # Brain extracted MNI0.7mm template
    params['t1templatebrain'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T1_'+ config['TemplateSize'] + '_brain.nii.gz'

    params['t2template'] = environ['HCPPIPEDIR_Templates'] + '/MNI152_T2_' + \
        config['TemplateSize'] + '.nii.gz'  # MNI0.7mm T2wTemplate
    params['t2templatebrain'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T2_' + config['TemplateSize'] + \
        '_brain.nii.gz'  # Brain extracted MNI0.7mm T2wTemplate
    params['t2template2mm'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T2_2mm.nii.gz'  # MNI2mm T2wTemplate
    params['templatemask'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T1_' + config['TemplateSize'] + \
        '_brain_mask.nii.gz'  # Brain mask MNI0.7mm template
    params['template2mmmask'] = environ['HCPPIPEDIR_Templates'] + \
        '/MNI152_T1_2mm_brain_mask_dil.nii.gz'  # MNI2mm template
    params['brainsize'] = config['BrainSize']
    params['fnirtconfig'] = environ['HCPPIPEDIR_Config'] + \
        '/T1_2_MNI152_2mm.cnf'  # FNIRT 2mm T1w Config

    # Parse Inputs
    # If SiemensFieldMap
    if (
        ('SiemensGREMagnitude' in inputs.keys()) and
        ('SiemensGREPhase' in inputs.keys())
    ):
        params['fmapmag'] = context.get_input_path('SiemensGREMagnitude')
        params['fmapphase'] = context.get_input_path('SiemensGREPhase')
        params['avgrdcmethod'] = "SiemensFieldMap"
        if (
          ('EchoTime' in inputs["SiemensGREMagnitude"]['object']['info'].keys()) and
          ('EchoTime' in inputs["SiemensGREPhase"]['object']['info'].keys())
        ):
            echotime1 = inputs["SiemensGREMagnitude"]['object']['info']['EchoTime']
            echotime2 = inputs["SiemensGREPhase"]['object']['info']['EchoTime']
            params['echodiff'] = format((echotime2 - echotime1) * 1000.0, '.15f')
    # Else if TOPUP
    elif (
        ('SpinEchoNegative' in inputs.keys()) and
        ('SpinEchoPositive' in inputs.keys())
    ):
        params['avgrdcmethod'] = "TOPUP"
        SpinEchoPhase1 = context.get_input_path("SpinEchoPositive")
        SpinEchoPhase2 = context.get_input_path("SpinEchoNegative")
        # Topup config if using TOPUP, set to NONE if using regular FIELDMAP
        params['topupconfig'] = environ['HCPPIPEDIR_Config'] + "/b02b0.cnf"
        if (
            'EffectiveEchoSpacing' in
            inputs["SpinEchoPositive"]['object']['info'].keys()
        ):  
            SEP_object_info = inputs["SpinEchoPositive"]['object']['info']
            SEN_object_info = inputs["SpinEchoNegative"]['object']['info']
            seechospacing = SEP_object_info['EffectiveEchoSpacing']
            params['seechospacing'] = format(seechospacing,'.15f')
                
            if (
                ('PhaseEncodingDirection' in SEP_object_info.keys())
                and
                ('PhaseEncodingDirection' in SEN_object_info.keys())
            ):
                pedirSE1 = SEP_object_info['PhaseEncodingDirection']
                pedirSE2 = SEN_object_info['PhaseEncodingDirection']
                pedirSE1 = tr("ijk", "xyz", pedirSE1)
                pedirSE2 = tr("ijk", "xyz", pedirSE2)
                # Check SpinEcho phase-encoding directions
                if (
                    ((pedirSE1, pedirSE2) == ("x", "x-")) or
                    ((pedirSE1, pedirSE2) == ("y", "y-"))
                ):
                    params['SEPhasePos'] = SpinEchoPhase1
                    params['SEPhaseNeg'] = SpinEchoPhase2
                elif (
                    ((pedirSE1, pedirSE2) == ("x-", "x")) or
                    ((pedirSE1, pedirSE2) == ("y-", "y"))
                ):
                    params['SEPhasePos'] = SpinEchoPhase2
                    params['SEPhaseNeg'] = SpinEchoPhase1
                    context.log.warning(
                        "SpinEcho phase-encoding directions were swapped. \
                         Continuing!")
                params['seunwarpdir'] = pedirSE1.replace(
                    '-', '').replace('+', '')
    # Else if General Electric Field Map
    elif "GeneralElectricFieldMap" in inputs.keys():
        # TODO: how do we handle GE fieldmap? where do we get deltaTE?
        raise Exception("Cannot currently handle GeneralElectricFieldmap!")

    params['unwarpdir'] = config['StructuralUnwarpDirection']
    if 'GradientCoeff' in inputs.keys():
        params['gdcoeffs'] = context.get_input_path('GradientCoeff')

    params['printcom'] = " "
    context.gear_dict['PRE-params'] = params

def validate(context):
    """
    Ensure that the PreFreeSurfer Parameters are valid.
    Raise Exceptions and exit if not valid.
    """
    params = context.gear_dict['PRE-params']
    inputs = context._invocation['inputs']
    # Examining Brain Size
    if params['brainsize'] < 10:
        context.log('Human Brains have a diameter larger than 1 cm!')
        context.log('Setting to defalut of 150 mm!')
        params['brainsize'] = 150
    # If "DwellTime" is not found in T1w/T2w, skip 
    # readout distortion correction
    if (params['t1samplespacing'] == "NONE") and \
       (params['t2samplespacing'] == "NONE"):
       if params['avgrdcmethod'] != "NONE":
            context.log.warning(
            '"DwellTime" tag not found. ' + \
            'Proceeding without readout distortion correction!'
            )
            params['avgrdcmethod'] = "NONE"
    # Examine Siemens Field Map input
    if (
        ('SiemensGREMagnitude' in inputs.keys()) and
        ('SiemensGREPhase' in inputs.keys())
    ):
        if 'echodiff' in params.keys():
            if params['echodiff'] == 0:
                raise Exception(
                    'EchoTime1 and EchoTime2 are the same \
                        (Please ensure Magnitude input is TE1)! Exiting.')
        else:
            raise Exception(
                'No EchoTime metadata found in FieldMap input file!  Exiting.')
    # Examine TOPUP input
    elif (
        ('SpinEchoNegative' in inputs.keys()) and
        ('SpinEchoPositive' in inputs.keys())
    ):
        if (
            ('PhaseEncodingDirection' in
             inputs["SpinEchoPositive"]['object']['info'].keys()) and
            ('PhaseEncodingDirection' in
             inputs["SpinEchoNegative"]['object']['info'].keys())
        ):
            pedirSE1 = \
                inputs["SpinEchoPositive"]['object']['info']['PhaseEncodingDirection']
            pedirSE2 = \
                inputs["SpinEchoNegative"]['object']['info']['PhaseEncodingDirection']
            pedirSE1 = tr("ijk", "xyz", pedirSE1)
            pedirSE2 = tr("ijk", "xyz", pedirSE2)
            if pedirSE1 == pedirSE2:
                raise Exception(
                    "SpinEchoPositive and SpinEchoNegative have the same \
                        PhaseEncodingDirection " + str(pedirSE1) + " !")
            if (
               not (( (pedirSE1, pedirSE2) == ("x", "x-")) or
                ( (pedirSE1, pedirSE2) ==  ("y","y-") )) and
               not (( (pedirSE1, pedirSE2) ==  ("x-", "x")) or
                ( (pedirSE1, pedirSE2) ==  ("y-","y")))
            ):
                    raise Exception(
                        "Unrecognized SpinEcho phase-encoding directions " +
                        str(pedirSE1) + ", " + str(pedirSE2) + ".")
        else:
            raise Exception(
                "SpinEchoPositive or SpinEchoNegative input \
                is missing PhaseEncodingDirection metadata!")
    elif "GeneralElectricFieldMap" in inputs.keys():
        raise Exception("Cannot currently handle GeneralElectricFieldmap!")

def execute(context):
    environ = context.gear_dict['environ']
    config = context.config
    os.makedirs(context.work_dir+'/'+ config['Subject'], exist_ok=True)
    command = []
    command.extend(context.gear_dict['command_common'])
    command.append(
               op.join(environ['HCPPIPEDIR'],'PreFreeSurfer',
               'PreFreeSurferPipeline.sh')
               )
    command = build_command_list(command,context.gear_dict['PRE-params'])

    stdout_msg = 'PreFreeSurfer logs (stdout, stderr) will be available ' + \
                 'in the file "pipeline_logs.zip" upon completion.'

    context.log.info('PreFreeSurfer command: \n')
    exec_command(context,command,stdout_msg = stdout_msg)
