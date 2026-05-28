#!/bin/bash
#kernel_change script for nvme / sda disks#

RED='\033[1;31m'
NC='\033[0m' # No Color
BOLDGREEN="\e[1;32m"
BOLDBLUE="\e[1;34m"

function check_uefi_legacy()
{
    boot_type=$([ -d /sys/firmware/efi ] && echo UEFI || echo BIOS)
    if [ $boot_type == "UEFI" ];
        then echo -e ${BOLDGREEN}"You are on UEFI BIOS MODE"${NC}
        else echo -e ${RED}"You are on LEGACY BIOS MODE"${NC}
             echo -e ${RED}"Running script for Legacy mode"${NC}
             echo -e ${RED}"Working on this ..."${NC} 
                exit 0
    fi
}



function add_exclude_dnf()
{
    sudo chattr -ia /etc/dnf/dnf.conf
    sudo cat /etc/dnf/dnf.conf | grep -w "#exclude"  > /dev/null 2>&1
    if echo $? -eq 1  > /dev/null 2>&1 ;
        then
            sudo sed -e '/exclude/ s/^#*/#/' -i /etc/dnf/dnf.conf
        else
            continue
    fi 
}

function add_exclude_yum()
{
    sudo cat /etc/yum.conf | grep -w "#exclude"  > /dev/null 2>&1
    if echo $? -eq 1 > /dev/null 2>&1 ;
        then
            sudo sed -e '/exclude/ s/^#*/#/' -i /etc/yum.conf  > /dev/null 2>&1
        else
            continue
    fi 
}

function remove_exclude_dnf()
{
    sudo chattr -ia /etc/dnf/dnf.conf
    sudo cat /etc/dnf/dnf.conf | grep -w "#exclude"  > /dev/null 2>&1
    if echo $? -eq 0  > /dev/null 2>&1;
        then
            sudo sed -i 's/#exclude/exclude/g' /etc/dnf/dnf.conf  > /dev/null 2>&1
            sudo chattr +ia /etc/dnf/dnf.conf
        else
            continue
    fi 
}

function remove_exclude_yum()
{
    sudo cat /etc/yum.conf | grep -w "#exclude"  > /dev/null 2>&1
    if echo $? -eq 0  > /dev/null 2>&1 ;
        then
            sudo sed -i 's/#exclude/exclude/g' /etc/yum.conf  > /dev/null 2>&1
        else
            continue
    fi 
}


function check_disk_mount()
{
    disk=$(fdisk -l | grep /dev/ | awk '{print $1}' | awk NR==2)
    if [ $disk == "/dev/nvme0n1p1" ]
    then sudo mount /dev/nvme0n1p1 /boot/efi 
    elif [ $disk == "/dev/sda1" ]
    then sudo mount /dev/sda1 /boot/efi
    fi

}

function get_kernel_name()
{
    #num_of_files=$(ls $path | grep kernel | wc -l)
    #echo $num_of_files
    kernel=$(ls $path | grep -w "kernel" |awk NR==1)
    #echo $kernel
    kernel_devel=$(ls $path | grep -w "kernel-devel")
    #echo $kernl_devel
    kernel_headers=$(ls $path | grep -w "kernel-headers")
    #echo $kernel_headers
    kernel_modules=$(ls $path | grep -w "kernel-modules")
    #echo $kernel_modules
    kernel_core=$(ls $path | grep -w "kernel-core")
    #echo $kernel_core
    kernel_modules_extra=$(ls $path | grep -w "kernel-modules-extra")
    all_kernel_modules=($kernel_headers $kernel_devel $kernel $kernel_modules $kernel_core)
}

function install_kernels()
{

    for i in ${all_kernel_modules[@]}
    do
            sudo dnf -y localinstall $path/$i --allowerasing > /dev/null 2>&1
            if echo $? -eq 0  > /dev/null 2>&1 ;
            then
                    echo -e  ${BOLDGREEN}" $i was successfully installed "${NC}
                    continue
            fi

    done        
}

function search_kernel_index()
{
    sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
    ls $path | grep kernel | awk NR==1 | cut -d '.' -f 1,2,3,4 > ~/kernel_name.txt
    kernel_name=$(sudo awk -F"[-_]" '{print $2 "-" $3}' ~/kernel_name.txt)
    echo "Kernel is:"
    echo -e ${BOLDBLUE}"$kernel_name"${NC}
    sleep 1
    kernel_index=$(sudo awk -F\' '$1=="menuentry " {print i++ " : " $2}' /boot/efi/EFI/fedora/grub.cfg | grep $kernel_name | awk '{print $1}')
    echo  -e ${BOLDBLUE}"Kernel index is : $kernel_index"${NC}
    echo "setting grub file to the relevant index"
    sudo sed -i "s/^GRUB_DEFAULT=.*/GRUB_DEFAULT=$kernel_index/" /etc/default/grub    

}

function create_grub_file()
{
    echo "Creating new grub file..."
    sleep 2
    sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
    echo -e ${BOLDBLUE} "Unmount disk ..."${NC}
    sudo  umount $disk
}

function reboot()
{
    echo -e ${BOLDGREEN}"host need reboot , you want to reboot now ? \n enter : y/n " ${NC}
    read answer
    if [ $answer == y ]
    then sudo reboot 
    elif [ $answer == n ]
    then  echo -e ${RED}"Don't forget to reboot the host :)"${NC}
    fi
    
}

function new_kernel()
{
    add_exclude_dnf 
    add_exclude_yum
    check_uefi_legacy
    check_disk_mount
    get_kernel_name
    install_kernels
    search_kernel_index
    create_grub_file
    remove_exclude_dnf
    remove_exclude_yum

    if $reboot_host; then
        reboot
    fi
}

#function change_kernel_legacy()
#{
#    check_disk_mount
#    get_kernel_name
#    install_kernels
#    grubby --set-default=/boot/vmlinuz-<make sure to take the kernel name in the bellow format>
#    grubby --set-default=/boot/vmlinuz-5.15.0_p22.gb92a3d6
#}

function print_help()
{
echo -e ${BOLDBLUE}"Script for install new kernel ver and set boot order to UEFI / Legacy BIOS modes "${NC}
  echo "------------------------------------------------------------------"
  echo "Usage : ./kernel_change.sh -[OPTIONS]"
  echo "Options:"
  echo "-r       Reboot after install relevant kernel"
  echo "-p       <path_to_kernel_folder_rpm_files>     (install the relevant kernel.rpm files)"
  echo "-h       Print this help message"
  echo "------------------------------------------------------------------"
  echo "Example:"
  echo "Without reboot: ./kernel_change.sh -p /home/sv10g/Downloads/mev-release-ci-6647/packages/x86_64/"
  echo "With reboot:    ./kernel_change.sh -r -p /home/sv10g/Downloads/mev-release-ci-6647/packages/x86_64/"

}

echo -e ${BOLDBLUE}"you can use -h for help"${NC}

reboot_host=false
while getopts "rp:h" opt; do
        case "${opt}" in
                r) reboot_host=true;;
                p) path=${OPTARG}; new_kernel ;;
                h) print_help ;;
        esac
done







