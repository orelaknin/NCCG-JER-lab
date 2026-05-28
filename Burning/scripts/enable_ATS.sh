#!/bin/bash

# Function to enable ATS
enable_ats() {
    sudo sed -i 's/^GRUB_CMDLINE_LINUX=".*"/GRUB_CMDLINE_LINUX="rhgb net.ifnames=0 biosdevname=0 intel_iommu=on iommu=on"/' /etc/default/grub
    update_grub
}

# Function to disable ATS
disable_ats() {
    sudo sed -i 's/^GRUB_CMDLINE_LINUX=".*"/GRUB_CMDLINE_LINUX="rhgb net.ifnames=0 biosdevname=0 intel_iommu=on iommu=pt pci=noats"/' /etc/default/grub
    update_grub
}

# Function to update GRUB configuration and ask for reboot
update_grub() {
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    sudo mount /dev/sda1 /mnt/
    sudo cp /boot/grub2/grub.cfg /mnt/EFI/fedora/grub.cfg
    read -p "Do you want to reboot now? (y/n): " choice
    case "$choice" in 
        y|Y ) sudo reboot;;
        n|N ) echo "Reboot aborted. Please reboot manually to apply changes.";;
        * ) echo "Invalid input. Reboot aborted. Please reboot manually to apply changes.";;
    esac
}

# Main script logic
case "$1" in
    on|ON )
        echo "Enabling ATS..."
        enable_ats
        ;;
    off|OFF )
        echo "Disabling ATS..."
        disable_ats
        ;;
    * )
        echo "Usage: $0 {on|off}"
        exit 1
        ;;
esac

