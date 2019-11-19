#!/bin/bash

set -e

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

qcmosaic1() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $1 x 10 ${2}.png 
}
qcmosaic2() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $2 $1 x 10 ${3}.png 
}

SubjectDIR=$1
T1wTemplate=$2
imgroot=$3

#set -x
qcmosaic1 ${SubjectDIR}/T1w/T1w_acpc_dc ${imgroot}acpc_T1 # T1 acpc
qcmosaic1 ${SubjectDIR}/T1w/T2w_acpc_dc ${imgroot}acpc_T2 # T2 acpc

qcmosaic1 ${SubjectDIR}/T1w/T1w_acpc_dc_restore ${imgroot}acpc_T1_biascorrected # T1 acpc after bias correction
qcmosaic1 ${SubjectDIR}/T1w/T2w_acpc_dc_restore ${imgroot}acpc_T2_biascorrected # T2 acpc after bias correction

qcmosaic2 ${SubjectDIR}/T1w/T1w_acpc_dc ${SubjectDIR}/T1w/T2w_acpc_dc ${imgroot}acpc_T2_T1xT2alignment # T2 acpc volume with T1 edges
qcmosaic2 ${SubjectDIR}/T1w/T2w_acpc_dc ${SubjectDIR}/T1w/T1w_acpc_dc ${imgroot}acpc_T1_T1xT2alignment # T1 acpc volume with T2 edges

qcmosaic2 ${SubjectDIR}/T1w/ribbon ${SubjectDIR}/T1w/T1w_acpc_dc_restore ${imgroot}acpc_T1_ribbon #T1 acpc with freesurfer edges
qcmosaic2 ${SubjectDIR}/T1w/ribbon ${SubjectDIR}/T1w/T2w_acpc_dc_restore ${imgroot}acpc_T2_ribbon #T2 acpc with freesurfer edges

qcmosaic2 ${T1wTemplate} ${SubjectDIR}/MNINonLinear/T1w_restore ${imgroot}mni_T1 # T1 MNI with template edges
qcmosaic2 ${T1wTemplate} ${SubjectDIR}/MNINonLinear/T2w_restore ${imgroot}mni_T2 # T2 MNI with template edges

#qcmosaic2 ${SubjectDIR}/MNINonLinear/ribbon ${SubjectDIR}/MNINonLinear/T1w_restore ${imgroot}mni_T1_ribbon
#qcmosaic2 ${SubjectDIR}/MNINonLinear/ribbon ${SubjectDIR}/MNINonLinear/T2w_restore ${imgroot}mni_T2_ribbon
