#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import tempfile
import tarfile
import argparse
import shutil
from glob import glob

# -----------------------------
# 1) MOUNT / UNMOUNT FUNCTIONS
# -----------------------------

def mount_remote_share(remote_path, mount_point, username=None, password=None):
    """
    Mounts a remote SMB share at the specified mount point.
    """
    # Ensure mount point exists
    if not os.path.exists(mount_point):
        os.makedirs(mount_point)
    
    mount_cmd = ["sudo", "mount", "-t", "cifs", remote_path, mount_point]
    
    options = []
    if username and password:
        options.append(f"username={username}")
        options.append(f"password={password}")
    # You can adjust the SMB version if needed (2.1, 3.0, 3.1.1, etc.)
    options.append("vers=3.0")

    if options:
        mount_cmd.extend(["-o", ",".join(options)])
    
    try:
        subprocess.run(mount_cmd, check=True)
        print(f"Mounted remote share {remote_path} to {mount_point}")
    except subprocess.CalledProcessError as e:
        print(f"Error mounting share: {e}")
        sys.exit(1)


def unmount_share(mount_point):
    """
    Safely unmount the share and clean up.
    """
    # Change directory back to something outside the mount to avoid "target is busy"
    os.chdir("/")

    try:
        subprocess.run(["sudo", "umount", mount_point], check=True)
        os.rmdir(mount_point)
        print(f"\nShare successfully unmounted: {mount_point}")
    except Exception as e:
        print(f"\nError unmounting share {mount_point}: {e}")


# -----------------------------
# 2) DETECT SSD (detect_ssd.py)
# -----------------------------

def check_disk_exists(disk_name):
    """
    Checks if the given disk name is detected by the system (fdisk).
    Returns True if found, False if not found (but doesn't exit).
    """
    check_disk = subprocess.run(["fdisk", "-l"], capture_output=True, text=True)
    
    if check_disk.returncode == 0:
        if disk_name in check_disk.stdout:
            print(f"\nNVMe is detected! ({disk_name})\n")
            return True
        else:
            print(f"\nNVMe {disk_name} is not detected!")
            print("Note: You can still use kernel installation features\n")
            return False
    else:
        print("\nError running fdisk -l\n")
        return False


# -------------------------
# 3) DIRECTORY NAVIGATION
# -------------------------

def list_directory_contents(directory_path):
    """
    Lists items (files/directories) at the given path, returning a list of names.
    Prints them with creation time and file type indicators for user selection.
    """
    if not os.path.isdir(directory_path):
        print(f"\nError: Directory '{directory_path}' does not exist.\n")
        return []
    
    directory_contents = os.listdir(directory_path)
    # Sort directory contents for consistency if desired
    directory_contents.sort()

    print(f"\nContents of: {directory_path}")
    print('{:>5}  {:<35}  {:>25}  {:<10}'.format("No.", "Name", "Creation Date", "Type"))
    print("-" * 80)
    
    for idx, item_name in enumerate(directory_contents, start=1):
        full_path = os.path.join(directory_path, item_name)
        creation_time = time.ctime(os.path.getctime(full_path))
        
        # Determine file type
        if os.path.isdir(full_path):
            file_type = "DIR"
        elif item_name.lower().endswith(('.tgz', '.tar.gz')):
            file_type = "KERNEL"
        elif item_name.lower().endswith(('.img', '.iso', '.bin', '.raw')):
            file_type = "IMAGE"
        else:
            file_type = "FILE"
        
        print('{:>5}  {:<35}  {:>25}  {:<10}'.format(idx, item_name[:35], creation_time, file_type))
    return directory_contents


def user_choose_item(directory_path):
    """
    Let user pick an item from directory_path. Return full path to that item.
    """
    while True:
        contents = list_directory_contents(directory_path)
        if not contents:
            print(f"\nNo items found in: {directory_path}. Returning.\n")
            return directory_path  # or None if you prefer

        user_input = input("\nEnter the number of the item to select, or 'q' to quit: ").strip()

        if user_input.lower() == 'q':
            return None
        
        try:
            choice = int(user_input)
            if 1 <= choice <= len(contents):
                chosen_name = contents[choice - 1]
                chosen_path = os.path.join(directory_path, chosen_name)
                # If it's a directory, go deeper
                if os.path.isdir(chosen_path):
                    directory_path = chosen_path  # keep going deeper
                else:
                    # It's a file, return it
                    return chosen_path
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")

# -------------------------
# 4) KERNEL MANAGEMENT (kernel_change.py equivalent)
# -------------------------

def check_uefi_mode():
    """
    Check if system is running in UEFI mode.
    """
    if os.path.exists("/sys/firmware/efi"):
        print("\nSystem is running in UEFI mode")
        return True
    else:
        print("\nSystem is running in Legacy BIOS mode")
        print("This script currently only supports UEFI mode")
        return False

def extract_tgz_file(tgz_path, extract_dir):
    """
    Extract a .tgz file to the specified directory.
    Enhanced to handle different archive formats and provide better error handling.
    """
    try:
        print(f"\nExtracting {os.path.basename(tgz_path)}...")
        
        # Method 1: Try simple tar command first (what you normally use)
        try:
            result = subprocess.run(
                ["tar", "-xvf", tgz_path, "-C", extract_dir],
                capture_output=True, text=True, check=True
            )
            print(f"Extraction completed to {extract_dir}")
            print("Files extracted:")
            # Show first few extracted files
            for line in result.stdout.split('\n')[:5]:
                if line.strip():
                    print(f"  - {line.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Simple tar failed: {e}")
            
        # Method 2: Try with gzip decompression
        try:
            result = subprocess.run(
                ["tar", "-xzvf", tgz_path, "-C", extract_dir],
                capture_output=True, text=True, check=True
            )
            print(f"Extraction completed to {extract_dir}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Gzip tar failed: {e}")
            
        # Method 3: Try with Python tarfile as fallback
        try:
            with tarfile.open(tgz_path, 'r:') as tar:
                tar.extractall(extract_dir)
            print(f"Extraction completed to {extract_dir}")
            return True
        except Exception as e:
            print(f"Python tarfile failed: {e}")
            
        # Method 4: Check what file type this actually is
        try:
            file_result = subprocess.run(['file', tgz_path], capture_output=True, text=True)
            print(f"File type detection: {file_result.stdout.strip()}")
        except:
            pass
        
        print("All extraction methods failed")
        return False
                    
    except Exception as e:
        print(f"Error extracting file: {e}")
        return False

def find_kernel_rpms(directory):
    """
    Find kernel RPM files in the given directory (recursively).
    """
    kernel_types = ['kernel-[0-9]*.rpm', 'kernel-devel*.rpm', 'kernel-headers*.rpm', 
                   'kernel-modules*.rpm', 'kernel-core*.rpm']
    
    found_rpms = []
    
    # Search recursively for kernel RPMs
    for root, dirs, files in os.walk(directory):
        for kernel_pattern in kernel_types:
            matches = glob(os.path.join(root, kernel_pattern))
            found_rpms.extend(matches)
    
    if found_rpms:
        print(f"\nFound {len(found_rpms)} kernel RPM files:")
        for rpm in found_rpms:
            print(f"  - {os.path.basename(rpm)}")
        return found_rpms
    else:
        print(f"\nNo kernel RPM files found in {directory}")
        return []

def disable_package_excludes():
    """
    Temporarily disable kernel excludes in DNF/YUM config.
    """
    try:
        # DNF config
        if os.path.exists("/etc/dnf/dnf.conf"):
            subprocess.run(["sudo", "chattr", "-ia", "/etc/dnf/dnf.conf"], check=True)
            subprocess.run(["sudo", "sed", "-e", "/exclude/ s/^#*/#/", "-i", "/etc/dnf/dnf.conf"], check=True)
        
        # YUM config
        if os.path.exists("/etc/yum.conf"):
            subprocess.run(["sudo", "sed", "-e", "/exclude/ s/^#*/#/", "-i", "/etc/yum.conf"], check=True)
        
        print("Package excludes temporarily disabled")
        return True
    except Exception as e:
        print(f"Error disabling package excludes: {e}")
        return False

def restore_package_excludes():
    """
    Restore kernel excludes in DNF/YUM config.
    """
    try:
        # DNF config
        if os.path.exists("/etc/dnf/dnf.conf"):
            subprocess.run(["sudo", "sed", "-i", "s/#exclude/exclude/g", "/etc/dnf/dnf.conf"], check=True)
            subprocess.run(["sudo", "chattr", "+ia", "/etc/dnf/dnf.conf"], check=True)
        
        # YUM config  
        if os.path.exists("/etc/yum.conf"):
            subprocess.run(["sudo", "sed", "-i", "s/#exclude/exclude/g", "/etc/yum.conf"], check=True)
        
        print("Package excludes restored")
        return True
    except Exception as e:
        print(f"Error restoring package excludes: {e}")
        return False

def mount_efi_partition():
    """
    Mount the EFI boot partition.
    """
    try:
        # Get disk information
        fdisk_output = subprocess.check_output(["fdisk", "-l"], text=True)
        
        efi_partition = None
        if "/dev/nvme0n1p1" in fdisk_output:
            efi_partition = "/dev/nvme0n1p1"
        elif "/dev/sda1" in fdisk_output:
            efi_partition = "/dev/sda1"
        
        if efi_partition:
            subprocess.run(["sudo", "mount", efi_partition, "/boot/efi"], check=True)
            print(f"Mounted EFI partition: {efi_partition}")
            return efi_partition
        else:
            print("No suitable EFI partition found")
            return None
    except Exception as e:
        print(f"Error mounting EFI partition: {e}")
        return None

def install_kernel_rpms(rpm_files):
    """
    Install kernel RPM files using DNF.
    """
    print(f"\nInstalling {len(rpm_files)} kernel packages...")
    
    success_count = 0
    for rpm_file in rpm_files:
        try:
            print(f"Installing {os.path.basename(rpm_file)}...")
            result = subprocess.run(
                ["sudo", "dnf", "-y", "localinstall", rpm_file, "--allowerasing"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print(f"  {os.path.basename(rpm_file)} installed successfully")
                success_count += 1
            else:
                print(f"  Failed to install {os.path.basename(rpm_file)}")
                print(f"  Error: {result.stderr}")
        except Exception as e:
            print(f"  Error installing {os.path.basename(rpm_file)}: {e}")
    
    print(f"\nInstallation summary: {success_count}/{len(rpm_files)} packages installed successfully")
    return success_count > 0

def update_grub_config(rpm_files):
    """
    Update GRUB configuration and set new kernel as default.
    This matches the logic from kernel_change.sh
    """
    try:
        print("\nUpdating GRUB configuration...")
        
        # Step 1: Generate initial GRUB config
        subprocess.run(
            ["sudo", "grub2-mkconfig", "-o", "/boot/efi/EFI/fedora/grub.cfg"],
            check=True
        )
        
        # Step 2: Extract kernel name from RPM files (similar to bash script)
        kernel_name = None
        main_kernel_rpm = None
        
        # Find the main kernel RPM (not devel, headers, modules, core)
        for rpm_file in rpm_files:
            rpm_basename = os.path.basename(rpm_file)
            if rpm_basename.startswith('kernel-') and not any(x in rpm_basename for x in ['devel', 'headers', 'modules', 'core']):
                main_kernel_rpm = rpm_basename
                break
        
        if main_kernel_rpm:
            # Extract version similar to bash script logic:
            # ls $path | grep kernel | awk NR==1 | cut -d '.' -f 1,2,3,4 > ~/kernel_name.txt
            # kernel_name=$(sudo awk -F"[-_]" '{print $2 "-" $3}' ~/kernel_name.txt)
            
            # Remove .rpm extension
            name_without_ext = main_kernel_rpm.replace('.rpm', '')
            
            # Split on dots and take first 4 parts (like cut -d '.' -f 1,2,3,4)
            dot_parts = name_without_ext.split('.')
            if len(dot_parts) >= 4:
                kernel_base = '.'.join(dot_parts[:4])
            else:
                kernel_base = name_without_ext
            
            # Now split on hyphens/underscores and take 2nd and 3rd parts
            parts = kernel_base.replace('_', '-').split('-')
            if len(parts) >= 3:
                kernel_name = f"{parts[1]}-{parts[2]}"
            else:
                # Fallback: try different approach
                if len(parts) >= 2:
                    kernel_name = parts[1]
        
        if not kernel_name:
            print("Warning: Could not determine kernel name from RPM files")
            print("GRUB default may need manual configuration")
            return True
        
        print(f"Kernel is: {kernel_name}")
        
        # Step 3: Find kernel index in GRUB config (matching bash script logic)
        grub_cfg = "/boot/efi/EFI/fedora/grub.cfg"
        
        try:
            # Parse GRUB config to find menu entries and their indices
            with open(grub_cfg, 'r') as f:
                grub_content = f.readlines()
            
            menu_entries = []
            line_index = 0
            for line in grub_content:
                if line.strip().startswith('menuentry '):
                    # Extract the menuentry title
                    # Format: menuentry 'title' --class ...
                    start = line.find("'")
                    end = line.find("'", start + 1)
                    if start != -1 and end != -1:
                        menu_title = line[start+1:end]
                        menu_entries.append((len(menu_entries), menu_title))
            
            # Find the entry that matches our kernel
            kernel_index = None
            for index, title in menu_entries:
                if kernel_name in title:
                    kernel_index = index
                    break
            
            if kernel_index is not None:
                print(f"Kernel index is: {kernel_index}")
                print("Setting grub file to the relevant index")
                
                # Step 4: Update /etc/default/grub with the correct default
                # Read current grub default file
                grub_default_file = "/etc/default/grub"
                
                # Update GRUB_DEFAULT setting
                subprocess.run([
                    "sudo", "sed", "-i", 
                    f"s/^GRUB_DEFAULT=.*/GRUB_DEFAULT={kernel_index}/", 
                    grub_default_file
                ], check=True)
                
                # Step 5: Regenerate GRUB config with new default
                print("Creating new grub file...")
                subprocess.run(
                    ["sudo", "grub2-mkconfig", "-o", "/boot/efi/EFI/fedora/grub.cfg"],
                    check=True
                )
                
                print(f"GRUB configuration updated successfully")
                print(f"Default kernel set to: {kernel_name} (index {kernel_index})")
                
            else:
                print(f"Warning: Could not find kernel {kernel_name} in GRUB menu")
                print("GRUB default may need manual configuration")
                
        except Exception as e:
            print(f"Error parsing GRUB config: {e}")
            print("GRUB configuration generated but default not set")
        
        return True
        
    except Exception as e:
        print(f"Error updating GRUB config: {e}")
        return False

def unmount_efi_partition(efi_partition):
    """
    Unmount the EFI partition.
    """
    try:
        if efi_partition:
            subprocess.run(["sudo", "umount", efi_partition], check=True)
            print(f"Unmounted EFI partition: {efi_partition}")
    except Exception as e:
        print(f"Error unmounting EFI partition: {e}")

def install_kernel_from_tgz(tgz_path, auto_reboot=False):
    """
    Complete workflow to install kernel from a .tgz file.
    """
    print(f"\nStarting kernel installation from {os.path.basename(tgz_path)}")
    
    # Check UEFI mode
    if not check_uefi_mode():
        return False
    
    # Create temporary directory for extraction
    temp_extract_dir = tempfile.mkdtemp(prefix="kernel_extract_")
    
    try:
        # Extract the .tgz file
        if not extract_tgz_file(tgz_path, temp_extract_dir):
            return False
        
        # Find kernel RPMs in extracted content
        rpm_files = find_kernel_rpms(temp_extract_dir)
        if not rpm_files:
            return False
        
        # Disable package excludes
        disable_package_excludes()
        
        # Mount EFI partition
        efi_partition = mount_efi_partition()
        
        # Install kernel packages
        install_success = install_kernel_rpms(rpm_files)
        
        if install_success:
            # Update GRUB configuration
            update_grub_config(rpm_files)
        
        # Cleanup
        unmount_efi_partition(efi_partition)
        restore_package_excludes()
        
        if install_success:
            print("\nKernel installation completed successfully!")
            
            if auto_reboot:
                print("Rebooting system...")
                subprocess.run(["sudo", "reboot"])
            else:
                response = input("\nReboot now to use the new kernel? (y/n): ").strip().lower()
                if response == 'y':
                    subprocess.run(["sudo", "reboot"])
                else:
                    print("Don't forget to reboot to activate the new kernel!")
        
        return install_success
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_extract_dir, ignore_errors=True)


# -------------------------
# 5) BURN IMAGE (burn.py)
# -------------------------

def burn_image_to_ssd(image_path, disk_name="/dev/nvme0n1"):
    """
    Uses dd to copy the given file to the NVMe device.
    """
    # Double-check that image_path is actually a file
    if not os.path.isfile(image_path):
        print(f"\nError: '{image_path}' is not a file.")
        return
    
    print(f"\nBurning {image_path} to {disk_name} ...")
    command_dd = ["sudo", "dd", f"if={image_path}", f"of={disk_name}", "status=progress"]

    subprocess.run(command_dd)
    print("Burn process completed.\n")


# --------------------------
# 6) MAIN SCRIPT / WORKFLOW
# --------------------------

def main():
    """
    Enhanced main function that can:
    1) Mount remote share to a temp dir.
    2) Detect /dev/nvme0n1 (optional for kernel operations).
    3) Let user navigate to find files (images or kernel packages).
    4) Handle both image burning and kernel installation.
    5) Unmount share.
    """
    parser = argparse.ArgumentParser(
        description="NVM Burner & Kernel Installer - Flash images and install kernels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 nvm_burner.py                    # Interactive mode
  python3 nvm_burner.py --auto-reboot      # Auto-reboot after kernel install
        """
    )
    parser.add_argument(
        "--auto-reboot", 
        action="store_true", 
        help="Automatically reboot after kernel installation"
    )
    
    args = parser.parse_args()
    
    # Configuration
    remote_path = "//ladjsvop.jer.intel.com/burn"
    mount_dir = os.path.join(tempfile.gettempdir(), "remote_burn_mount")
    disk_name = "/dev/nvme0n1"

    # Credentials
    username = "laduser"
    password = "$giga"

    print("NVM Burner & Kernel Installer")
    print("=================================")

    # 1) Mount
    mount_remote_share(remote_path, mount_dir, username, password)

    # 2) Check NVMe presence (but don't exit if not found)
    disk_available = check_disk_exists(disk_name)

    # 3) Let user navigate deeper to find a file
    chosen_file = user_choose_item(mount_dir)
    if not chosen_file:
        print("No file chosen. Exiting...")
        unmount_share(mount_dir)
        sys.exit(0)

    # 4) Determine file type and take appropriate action
    file_extension = os.path.splitext(chosen_file)[1].lower()
    filename = os.path.basename(chosen_file).lower()
    
    if filename.endswith('.tgz') or filename.endswith('.tar.gz'):
        print(f"\nDetected kernel package: {os.path.basename(chosen_file)}")
        
        # Check if this looks like a kernel package
        if any(keyword in filename for keyword in ['kernel', 'mev', 'ipu']):
            response = input("This appears to be a kernel package. Install kernel? (y/n): ").strip().lower()
            if response == 'y':
                success = install_kernel_from_tgz(chosen_file, args.auto_reboot)
                if not success:
                    print("Kernel installation failed")
            else:
                print("Skipping kernel installation")
        else:
            print("File is compressed but doesn't appear to be a kernel package")
            if disk_available:
                response = input("Burn this file as an image instead? (y/n): ").strip().lower()
                if response == 'y':
                    burn_image_to_ssd(chosen_file, disk_name)
            else:
                print("Cannot burn image - no NVMe drive detected")
    
    elif file_extension in ['.img', '.iso', '.bin', '.raw'] or os.path.isfile(chosen_file):
        print(f"\nDetected image file: {os.path.basename(chosen_file)}")
        if disk_available:
            response = input("Burn this image to NVMe drive? (y/n): ").strip().lower()
            if response == 'y':
                burn_image_to_ssd(chosen_file, disk_name)
            else:
                print("Skipping image burning")
        else:
            print("Cannot burn image - no NVMe drive detected")
            print("Note: Only kernel installation is available without NVMe")
    
    else:
        print(f"\nUnknown file type: {os.path.basename(chosen_file)}")
        print("File operations:")
        if disk_available:
            print("1. Burn as image")
            print("2. Try as kernel package (if .tgz)")
            print("3. Cancel")
            
            choice = input("Choose option (1-3): ").strip()
            if choice == '1':
                burn_image_to_ssd(chosen_file, disk_name)
            elif choice == '2' and (filename.endswith('.tgz') or filename.endswith('.tar.gz')):
                install_kernel_from_tgz(chosen_file, args.auto_reboot)
            else:
                print("No action taken")
        else:
            print("1. Try as kernel package (if .tgz)")
            print("2. Cancel")
            
            choice = input("Choose option (1-2): ").strip()
            if choice == '1' and (filename.endswith('.tgz') or filename.endswith('.tar.gz')):
                install_kernel_from_tgz(chosen_file, args.auto_reboot)
            else:
                print("No action taken")

    # 5) Unmount
    unmount_share(mount_dir)
    print("\nProcess complete.")


if __name__ == "__main__":
    main()

