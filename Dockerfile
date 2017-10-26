# Creates docker container that runs bxh-xcede-tools fmriqa algorithms
#
#

# Use Ubuntu 14.04 LTS
#FROM ubuntu:trusty-20170119

FROM ubuntu:trusty-20170817

# Use Ubuntu 16.04 (required for MSM ubuntu binary) - replace all "14.04" with "16.04", and all "trusty" with "xenial"
#FROM ubuntu:xenial-20170915

MAINTAINER Flywheel <support@flywheel.io>

# Install packages
RUN apt-get update \
    && apt-get install -y \
    lsb-core \
    bsdtar \
    zip \
    unzip \
    gzip \
    curl \
    jq \
    python-pip


# Add non-free sources
#RUN echo deb http://neurodeb.pirsquared.org data main contrib non-free >> /etc/apt/sources.list.d/neurodebian.sources.list
#RUN echo deb http://neurodeb.pirsquared.org xenial main contrib non-free >> /etc/apt/sources.list.d/neurodebian.sources.list

# Install the validator
#RUN apt-get update && \
#    apt-get install -y curl && \
#    curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
#    apt-get remove -y curl && \
#    apt-get install -y nodejs && \
#    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

#RUN npm install -g bids-validator@0.19.2

# Download FreeSurfer
RUN apt-get -y update \
    && apt-get install -y wget && \
    wget -qO- ftp://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/5.3.0-HCP/freesurfer-Linux-centos4_x86_64-stable-pub-v5.3.0-HCP.tar.gz | tar zxv -C /opt \
    --exclude='freesurfer/trctrain' \
    --exclude='freesurfer/subjects/fsaverage_sym' \
    --exclude='freesurfer/subjects/fsaverage3' \
    --exclude='freesurfer/subjects/fsaverage4' \
    --exclude='freesurfer/subjects/fsaverage5' \
    --exclude='freesurfer/subjects/fsaverage6' \
    --exclude='freesurfer/subjects/cvs_avg35' \
    --exclude='freesurfer/subjects/cvs_avg35_inMNI152' \
    --exclude='freesurfer/subjects/bert' \
    --exclude='freesurfer/subjects/V1_average' \
    --exclude='freesurfer/average/mult-comp-cor' \
    --exclude='freesurfer/lib/cuda' \
    --exclude='freesurfer/lib/qt' && \
    apt-get install -y tcsh bc tar libgomp1 perl-modules curl  && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set up the environment
ENV OS Linux
ENV FS_OVERRIDE 0
ENV FIX_VERTEX_AREA=
ENV SUBJECTS_DIR /opt/freesurfer/subjects
ENV FSF_OUTPUT_FORMAT nii.gz
ENV MNI_DIR /opt/freesurfer/mni
ENV LOCAL_DIR /opt/freesurfer/local
ENV FREESURFER_HOME /opt/freesurfer
ENV FSFAST_HOME /opt/freesurfer/fsfast
ENV MINC_BIN_DIR /opt/freesurfer/mni/bin
ENV MINC_LIB_DIR /opt/freesurfer/mni/lib
ENV MNI_DATAPATH /opt/freesurfer/mni/data
ENV FMRI_ANALYSIS_DIR /opt/freesurfer/fsfast
ENV PERL5LIB /opt/freesurfer/mni/lib/perl5/5.8.5
ENV MNI_PERL5LIB /opt/freesurfer/mni/lib/perl5/5.8.5
ENV PATH /opt/freesurfer/bin:/opt/freesurfer/fsfast/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

# Install FSL 5.0.9
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -sSL http://neuro.debian.net/lists/trusty.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pgp.mit.edu:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y fsl-core=5.0.9-4~nd14.04+1 && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Configure environment
ENV FSLDIR=/usr/share/fsl/5.0
ENV FSL_DIR="${FSLDIR}"
ENV FSLOUTPUTTYPE=NIFTI_GZ
ENV PATH=/usr/lib/fsl/5.0:$PATH
ENV FSLMULTIFILEQUIT=TRUE
ENV POSSUMDIR=/usr/share/fsl/5.0
ENV LD_LIBRARY_PATH=/usr/lib/fsl/5.0:$LD_LIBRARY_PATH
ENV FSLTCLSH=/usr/bin/tclsh
ENV FSLWISH=/usr/bin/wish
ENV FSLOUTPUTTYPE=NIFTI_GZ

# Create freesurfer license file (currently base64 encoded from BIDS)
RUN echo "cHJpbnRmICJrcnp5c3p0b2YuZ29yZ29sZXdza2lAZ21haWwuY29tXG41MTcyXG4gKkN2dW12RVYzelRmZ1xuRlM1Si8yYzFhZ2c0RVxuIiA+IC9vcHQvZnJlZXN1cmZlci9saWNlbnNlLnR4dAo=" | base64 -d | sh

# Install Connectome Workbench
RUN apt-get update && apt-get -y install connectome-workbench=1.2.3-1~nd14.04+1

ENV CARET7DIR=/usr/bin


# Install gradient unwarp script
# note: python-dev needed for Ubuntu 14.04 (but not for 16.04)
# latest = v1.0.3
# This commit fixes the memory bug: bab8930e37f1b8ad3a7e274b07c5b3f0f096be85
RUN apt-get -y update \
    && apt-get install -y --no-install-recommends python-dev && \
    apt-get install -y --no-install-recommends python-numpy && \
    apt-get install -y --no-install-recommends python-scipy && \
    apt-get install -y --no-install-recommends python-nibabel && \
    wget https://github.com/Washington-University/gradunwarp/archive/bab8930e37f1b8ad3a7e274b07c5b3f0f096be85.tar.gz -O gradunwarp.tar.gz && \
    cd /opt/ && \
    tar zxvf /gradunwarp.tar.gz && \
    mv /opt/gradunwarp-* /opt/gradunwarp && \
    cd /opt/gradunwarp/ && \
    python setup.py install && \
    rm /gradunwarp.tar.gz && \
    cd / && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install HCP Pipelines

#latest v3.x = v3.22.0
#latest v4.x = v4.0.0-alpha.5
#Ugh... need to use this commit to fix bugs in v4.0.0-alpha.5: 90b0766636ba83f06c9198206cc7fa90117b0b11
RUN apt-get -y update \
    && apt-get install -y --no-install-recommends python-numpy && \
    wget https://github.com/Washington-University/Pipelines/archive/90b0766636ba83f06c9198206cc7fa90117b0b11.tar.gz -O pipelines.tar.gz && \
    cd /opt/ && \
    tar zxvf /pipelines.tar.gz && \
    mv /opt/Pipelines-* /opt/HCP-Pipelines && \
    rm /pipelines.tar.gz && \
    cd / && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV HCPPIPEDIR=/opt/HCP-Pipelines

#############################################
# Install MSM binaries (from local directory)
ENV MSMBin=${HCPPIPEDIR}/MSMBinaries

# Copy MSM_HOCR_v2 binary, and latest HCP MSM config
#COPY MSM/Ubuntu/msm ${MSMBin}/msm
COPY MSM/Centos/msm ${MSMBin}/msm

#For Pipeline v3.x:
#COPY MSM/MSMSulcStrainFinalconf ${MSMBin}/allparameterssulcDRconf
#############################################

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Copy executable/manifest to Gear
COPY run ${FLYWHEEL}/run
COPY manifest.json ${FLYWHEEL}/manifest.json

# Copy additional scripts and scenes
COPY scripts/*.sh scripts/*.bat ${FLYWHEEL}/scripts/
COPY scenes/TEMPLATE*.scene ${FLYWHEEL}/scenes/

# ENV preservation for Flywheel Engine
RUN env -u HOSTNAME -u PWD | \
  awk -F = '{ print "export " $1 "=\"" $2 "\"" }' > ${FLYWHEEL}/docker-env.sh

# Configure entrypoint
ENTRYPOINT ["/flywheel/v0/run"]
