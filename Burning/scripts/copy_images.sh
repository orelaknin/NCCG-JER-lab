#!/bin/bash


ION_SERVER='ivnc0349.iil.intel.com'
BKC_SERVER='/net/ladhdatamevpo.iil.intel.com'
BKC_DIR="/net/ladhdatamevpo.iil.intel.com/data/BKC_releases"
LAAS_MEV_LOG_DIR="/nfs/iil/disks/ipu-fw_reg_mev/MEV_regression/JenkinsCI_SV"
USER='svtools'
PASS='SVSW@123'


get_images() {
	
	IMAGE_DIR="$LAAS_MEV_LOG_DIR/$LAAS_LOG/Images"
	echo "copying $IMAGE_DIR images from laas server"
	if [ "$PROJECT" = 'mev' ]; then
		BKC_PROJECT_DIR="$BKC_DIR/MEV"
	fi
	mkdir $BKC_PROJECT_DIR/$RELEASE_NAME
	
	echo "Command: scp -r -o StrictHostKeyChecking=no $USER@$ION_SERVER:$IMAGE_DIR/ $BKC_PROJECT_DIR/$RELEASE_NAME"
	
	/usr/bin/expect <<- EOF
    	set timeout -1
    	spawn bash -c "scp -r -o StrictHostKeyChecking=no $USER@$ION_SERVER:/$IMAGE_DIR/ $BKC_PROJECT_DIR/$RELEASE_NAME"
    	expect {
        	"Password:" { send "${PASS}\r"; exp_continue }
        	eof
   	 }
   
    	catch wait result
    	exit [lindex \$result 3]
	EOF
	
	#expect -timeout -1 eof
	if [ $? -ne 0 ]; then
	    	echo "Copy failed"
		rm -rf $BKC_PROJECT_DIR/$RELEASE_NAME
        	exit 1
	else
    		echo "Create latest tag for the latest ci $RELEASE_NAME"
    		cd $BKC_PROJECT_DIR
    		ln -sfn $RELEASE_NAME latest
	fi
			
}

while (( "$#" )); do
	case "$1" in
	-p)		PROJECT=$2
			echo "PROJECT: $PROJECT"
			shift
			;;
	-l)		LAAS_LOG=$2
			echo "LAAS_LOG: $LAAS_LOG"
			;;
	-n)		RELEASE_NAME=$2
			echo "RELEASE_NAME: $RELEASE_NAME"
			;;
	-h)		echo "Usage:"
			echo "-p (project): <mev/mmg>"
			echo "-n (name) release name e.g.-n mev-ci-release"
			echo "-l (laas log): e.g SV_CommonEntry_K8s_ORAMA_CIDC-49"
			echo " e.g. copy_images.sh -p mev -pt si -l SV_CommonEntry_K8s_ORAMA_CIDC-49"
			exit 0
			;;
	esac
	shift
done

[ -z $PROJECT ] && echo "PROJECT required. e.g. -p mev/mmg" && exit 1
[ -z $LAAS_LOG ] && echo "RELEASE_NAME required. e.g. -n mev-ci-release" && exit 1
[ -z $RELEASE_NAME ] && echo "LAAS_LOG required. e.g. -l SV_CommonEntry_K8s_ORAMA_CIDC-49" && exit 1
get_images
