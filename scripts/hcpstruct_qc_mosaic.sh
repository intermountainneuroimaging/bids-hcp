#!/bin/bash

set -e

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# Main script that will accept substitutions below.
qcmosaic1() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $1 x 10 ${2}.png 
}
qcmosaic2() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $2 $1 x 10 ${3}.png 
}

subject_dir=$1
T1wTemplate=$2
imgroot=$3

#set -x
# Set and run the substitutions.
qcmosaic1 ${subject_dir}/T1w/T1w_acpc_dc ${imgroot}acpc_T1 # T1 acpc
if [ -f "${subject_dir}/T1w/T2w_acpc_dc" ]; then
  qcmosaic1 ${subject_dir}/T1w/T2w_acpc_dc ${imgroot}acpc_T2 # T2 acpc
fi

qcmosaic1 ${subject_dir}/T1w/T1w_acpc_dc_restore ${imgroot}acpc_T1_biascorrected # T1 acpc after bias correction
if [ -f "${subject_dir}/T1w/T2w_acpc_dc_restore" ]; then
  qcmosaic1 ${subject_dir}/T1w/T2w_acpc_dc_restore ${imgroot}acpc_T2_biascorrected # T2 acpc after bias correction
fi

if [ -f "${subject_dir}/T1w/T2w_acpc_dc" ]; then
  qcmosaic2 ${subject_dir}/T1w/T1w_acpc_dc ${subject_dir}/T1w/T2w_acpc_dc ${imgroot}acpc_T2_T1xT2alignment # T2 acpc volume with T1 edges
  qcmosaic2 ${subject_dir}/T1w/T2w_acpc_dc ${subject_dir}/T1w/T1w_acpc_dc ${imgroot}acpc_T1_T1xT2alignment # T1 acpc volume with T2 edges
fi

qcmosaic2 ${subject_dir}/T1w/ribbon ${subject_dir}/T1w/T1w_acpc_dc_restore ${imgroot}acpc_T1_ribbon #T1 acpc with freesurfer edges
if [ -f "${subject_dir}/T1w/T2w_acpc_dc_restore" ]; then
  qcmosaic2 ${subject_dir}/T1w/ribbon ${subject_dir}/T1w/T2w_acpc_dc_restore ${imgroot}acpc_T2_ribbon #T2 acpc with freesurfer edges
fi

qcmosaic2 ${T1wTemplate} ${subject_dir}/MNINonLinear/T1w_restore ${imgroot}mni_T1 # T1 MNI with template edges
if [ -f "${subject_dir}/T1w/T2w_restore" ]; then
  qcmosaic2 ${T1wTemplate} ${subject_dir}/MNINonLinear/T2w_restore ${imgroot}mni_T2 # T2 MNI with template edges
fi

#qcmosaic2 ${subject_dir}/MNINonLinear/ribbon ${subject_dir}/MNINonLinear/T1w_restore ${imgroot}mni_T1_ribbon
#qcmosaic2 ${subject_dir}/MNINonLinear/ribbon ${subject_dir}/MNINonLinear/T2w_restore ${imgroot}mni_T2_ribbon
