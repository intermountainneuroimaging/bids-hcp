#!/bin/bash

set -e


SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

qcmosaic1() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $1 x 10 ${2}.png 
}
qcmosaic2() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $2 $1 x 10 ${3}.png 
}

#2mm version of mosaics, skip fewer slices and do upscale at end
qcmosaic1_2mm() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $1 x 5 ${2}.png -n -s 2
}
qcmosaic2_2mm() { 
  bash ${SCRIPT_DIR}/volmosaic.sh $2 $1 x 5 ${3}.png -n -s 2
}

SubjectDIR=$1
DWIName=$2
imgroot=$3

#DiffRes=`${FSLDIR}/bin/fslval ${SubjectDIR}/${DWIName}/data/data pixdim1`
#DiffRes=`printf "%0.2f" ${DiffRes}`

#######################################################

diffdir=${SubjectDIR}/${DWIName}/data
fitroot=${diffdir}/dtifit

gradarg=""
if [ ! -z `imglob ${diffdir}/grad_dev` ]; then
  gradarg="--gradnonlin=${diffdir}/grad_dev"
fi

#maybe use --kurt option if available?

echo "Running dtifit to generate FA maps..."
${FSLDIR}/bin/dtifit \
  --data=${diffdir}/data \
  --bvecs=${diffdir}/bvecs \
  --bvals=${diffdir}/bvals \
  --mask=${diffdir}/nodif_brain_mask \
  --out=${fitroot} --sse ${gradarg}


#non-diff, FA, and sse in native space
qcmosaic1_2mm ${diffdir}/nodif ${imgroot}nodif
qcmosaic1_2mm ${fitroot}_FA ${imgroot}dtifit_FA
qcmosaic1_2mm ${fitroot}_sse ${imgroot}dtifit_sse

qctmp=${diffdir}/qctmp

# non-diffusion (B=0) volume in T1 space, with T1w edges overlaid, and freesurfer ribbon edges overlaid
${FSLDIR}/bin/applywarp --interp=spline \
  -i ${diffdir}/nodif \
  --premat=${diffdir}/../reg/diff2str.mat \
  -r ${SubjectDIR}/T1w/T1w_acpc_dc_restore_brain \
  -o ${qctmp} \
  --interp=spline \
 && qcmosaic2 ${SubjectDIR}/T1w/T1w_acpc_dc_restore ${qctmp} ${imgroot}reg2T1_nodif \
 && qcmosaic2 ${SubjectDIR}/T1w/ribbon ${qctmp} ${imgroot}reg2T1_nodif_fsribbon \
 && ${FSLDIR}/bin/imrm ${qctmp}

# dtifit FA in T1 space, with T1w edges overlaid
${FSLDIR}/bin/applywarp --interp=spline \
  -i ${fitroot}_FA \
  --premat=${diffdir}/../reg/diff2str.mat \
  -r ${SubjectDIR}/T1w/T1w_acpc_dc_restore_brain \
  -o ${qctmp} \
  --interp=spline \
 && qcmosaic2 ${SubjectDIR}/T1w/T1w_acpc_dc_restore ${qctmp} ${imgroot}reg2T1_dtifit_FA \
 && ${FSLDIR}/bin/imrm ${qctmp}

# dtifit sse (dti residual) in T1 space, with T1w edges overlaid
${FSLDIR}/bin/applywarp --interp=spline \
  -i ${fitroot}_sse \
  --premat=${diffdir}/../reg/diff2str.mat \
  -r ${SubjectDIR}/T1w/T1w_acpc_dc_restore_brain \
  -o ${qctmp} \
  --interp=spline \
 && qcmosaic2 ${SubjectDIR}/T1w/T1w_acpc_dc_restore ${qctmp} ${imgroot}reg2T1_dtifit_sse \
 && ${FSLDIR}/bin/imrm ${qctmp}

rm -f ${fitroot}_*

