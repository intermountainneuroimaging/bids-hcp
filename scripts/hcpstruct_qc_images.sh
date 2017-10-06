#! /bin/bash

set -e

#SCRIPTDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
#templatescene=${SCRIPTDIR}/scenes/hcpstruct.QCtemplate.164k_fs_LR.scene.tar.gz
#newsubj=111111
#newroot=/home/keithj/testdata/hcp-struct/output/111111/
#newscene=${newroot}/${newsubj}.hcpstruct_QC.scene
#newscene=./${newsubj}.hcpstruct_QC.scene
#imgroot=${newsubj}.164k_fs_LR.

#imgparams="1440 900"

templatescene=$1
newscene=$2
newsubj=$3
newroot=$4
imgroot=$5
shift 5

imgparams=$@


templatesubj="__TEMPLATE_HCPSTRUCT_SUBJECT_NAME__"
templateroot="__TEMPLATE_HCPSTRUCT_SUBJECT_ROOTDIR__"


catcmd="cat"
if [[ "$templatescene" == *.tar.gz  ]]; then
	catcmd="tar -xOzf"
fi

${catcmd} ${templatescene} | tr '\n' '\v' | sed -E 's#"png">.+</Image>#"png"></Image>#g' | tr '\v' '\n' \
| sed 's#'${templateroot}'#'${newroot}'#g' \
| sed 's#'${templatesubj}'#'${newsubj}'#g' \
> ${newscene}

# step 3: for subject, run through QC scene and generate figures
scenenames=$( wb_command -file-information $newscene | grep -E '^#[0-9]+[[:space:]].+:[[:space:]]*$' | sed -E 's/^#([0-9]+)[[:space:]]+(.+):[[:space:]]*$/\1@\2/' )

for s in $scenenames; do
    scenenum=${s/@*/""}
    scenename=${s/*@/""}
		echo -e "###################"
		echo -e "Generating QC image #${scenenum} ${imgroot}${scenename}.png"
    wb_command -show-scene $newscene $scenenum ${imgroot}${scenename}.png $imgparams 2>&1
done
