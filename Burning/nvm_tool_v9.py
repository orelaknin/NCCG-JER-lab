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

def get_target_kernel_version(rpm_files):
    """
    Extract the target kernel version from the main kernel RPM file.
    """
    main_kernel_rpm = None
    
    # Find the main kernel RPM (not devel, headers, modules, core)
    for rpm_file in rpm_files:
        rpm_basename = os.path.basename(rpm_file)
        if rpm_basename.startswith('kernel-') and not any(x in rpm_basename for x in ['devel', 'headers', 'modules', 'core']):
            main_kernel_rpm = rpm_basename
            break
    
    if main_kernel_rpm:
        # Extract version from kernel RPM filename
        # Example: kernel-6.6.4_p16.gcef50f0+-1.x86_64.rpm -> 6.6.4-p16.gcef50f0+
        name_without_ext = main_kernel_rpm.replace('.rpm', '')
        version_part = name_without_ext[7:]  # Remove 'kernel-'
        # Remove the last part (architecture and build number)
        if '-' in version_part:
            parts = version_part.split('-')
            if len(parts) >= 2:
                # Rejoin all but the last part, and replace '_' with '-'
                kernel_version = '-'.join(parts[:-1]).replace('_', '-')
                return kernel_version
    
    return None

def run_kernel_commit_interactive():
    """
    Run the kernel_commit.sh script interactively to set the default kernel.
    """
    print("\n" + "="*80)
    print("KERNEL COMMIT - Setting Default Kernel")
    print("="*80)
    print("The kernel installation is complete. Now we need to set it as the default.")
    print("The kernel_commit script will show you available kernels.")
    print("Please select the newly installed kernel from the list.")
    print("="*80)
    
    # List of possible kernel_commit locations to try
    kernel_commit_paths = [
        "/net/inx028core.intel.com/data/things/scripts/kernel_commit.sh",  # From the alias
        "./kernel_commit.sh",  # Current directory
        "/usr/local/bin/kernel_commit.sh",  # Common install location
        "/opt/scripts/kernel_commit.sh",  # Another common location
    ]
    
    kernel_commit_cmd = None
    
    # First try to use the alias if it exists
    try:
        # Check if kernel_commit alias exists by running it in bash
        result = subprocess.run(
            ["bash", "-c", "type kernel_commit"], 
            capture_output=True, text=True
        )
        if result.returncode == 0 and "alias" in result.stdout:
            print("Found kernel_commit alias")
            kernel_commit_cmd = ["bash", "-c", "kernel_commit"]
        else:
            print("kernel_commit alias not found, trying direct paths...")
    except:
        pass
    
    # If alias didn't work, try direct paths
    if not kernel_commit_cmd:
        for path in kernel_commit_paths:
            if os.path.exists(path):
                print(f"Found kernel_commit script at: {path}")
                kernel_commit_cmd = ["sudo", "bash", path]
                break
    
    if not kernel_commit_cmd:
        print("Error: kernel_commit script not found in any of these locations:")
        for path in kernel_commit_paths:
            print(f"  - {path}")
        print("\nPlease run 'kernel_commit' manually to set the default kernel")
        return False
    
    try:
        # Run kernel_commit interactively
        print("Starting kernel_commit script...\n")
        result = subprocess.run(kernel_commit_cmd, text=True)
        
        if result.returncode == 0:
            print("\nKernel commit completed successfully!")
            return True
        else:
            print(f"\nKernel commit failed with return code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"Error running kernel_commit: {e}")
        return False

def run_kernel_commit_auto(target_kernel_version):
    """
    Try to automatically select the target kernel in kernel_commit script.
    Falls back to interactive mode if automatic selection fails.
    """
    print("\n" + "="*80)
    print("KERNEL COMMIT - Setting Default Kernel")
    print("="*80)
    print(f"Attempting to automatically set kernel: {target_kernel_version}")
    print("="*80)
    
    # List of possible kernel_commit locations to try
    kernel_commit_paths = [
        "/net/inx028core.intel.com/data/things/scripts/kernel_commit.sh",  # From the alias
        "./kernel_commit.sh",  # Current directory
        "/usr/local/bin/kernel_commit.sh",  # Common install location
        "/opt/scripts/kernel_commit.sh",  # Another common location
    ]
    
    kernel_commit_cmd = None
    
    # First try to use the alias if it exists
    try:
        # Check if kernel_commit alias exists by running it in bash
        result = subprocess.run(
            ["bash", "-c", "type kernel_commit"], 
            capture_output=True, text=True
        )
        if result.returncode == 0 and "alias" in result.stdout:
            print("Found kernel_commit alias")
            kernel_commit_cmd = ["bash", "-c", "kernel_commit"]
        else:
            print("kernel_commit alias not found, trying direct paths...")
    except:
        pass
    
    # If alias didn't work, try direct paths
    if not kernel_commit_cmd:
        for path in kernel_commit_paths:
            if os.path.exists(path):
                print(f"Found kernel_commit script at: {path}")
                kernel_commit_cmd = ["sudo", "bash", path]
                break
    
    if not kernel_commit_cmd:
        print("Error: kernel_commit script not found in any of these locations:")
        for path in kernel_commit_paths:
            print(f"  - {path}")
        print("\nFalling back to interactive mode...")
        return run_kernel_commit_interactive()
    
    try:
        # Get the list of available kernels first
        grubby_result = subprocess.run([
            "bash", "-c", 
            "grubby --info=ALL | grep title= | grep -oP 'title=\"\\K[^\"]+'"
        ], capture_output=True, text=True)
        
        if grubby_result.returncode != 0:
            print("Could not get kernel list, falling back to interactive mode")
            return run_kernel_commit_interactive()
        
        kernel_titles = [line.strip() for line in grubby_result.stdout.split('\n') if line.strip()]
        target_index = None
        
        # Find the index of our target kernel
        for i, title in enumerate(kernel_titles, 1):
            if target_kernel_version in title:
                target_index = i
                print(f"Found target kernel at index {target_index}: {title}")
                break
        
        if target_index is None:
            print(f"Could not find kernel {target_kernel_version} in available kernels")
            print("Falling back to interactive mode...")
            return run_kernel_commit_interactive()
        
        # Try to run kernel_commit with automatic input
        print(f"Automatically selecting kernel option {target_index}...")
        
        # Use expect-like behavior to send the selection automatically
        process = subprocess.Popen(
            kernel_commit_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Send the selection
        stdout, stderr = process.communicate(input=f"{target_index}\n")
        
        print("kernel_commit output:")
        print(stdout)
        
        if process.returncode == 0:
            print(f"\nKernel {target_kernel_version} set as default successfully!")
            return True
        else:
            print(f"\nAutomatic kernel commit failed, falling back to interactive mode...")
            return run_kernel_commit_interactive()
            
    except Exception as e:
        print(f"Error in automatic kernel commit: {e}")
        print("Falling back to interactive mode...")
        return run_kernel_commit_interactive()

def install_kernel_from_tgz(tgz_path, auto_reboot=False):
    """
    Complete workflow to install kernel from a .tgz file.
    Uses kernel_commit.sh for reliable GRUB configuration.
    Checks for an existing backup in ~/ named after tgz_path basename and uses it if available.
    Copies the extracted folder to the user's home directory named after tgz_path basename,
    only if the .tgz file was extracted (not if backup was used).
    """
    print(f"\nStarting kernel installation from {os.path.basename(tgz_path)}")
    
    # Check UEFI mode
    if not check_uefi_mode():
        return False
    
    # Create temporary directory for extraction
    temp_extract_dir = tempfile.mkdtemp(prefix="kernel_extract_")
    
    try:
        # Determine backup folder path
        backup_dir = os.path.expanduser("~/")
        tgz_basename = os.path.splitext(os.path.basename(tgz_path))[0]
        safe_tgz_name = tgz_basename.replace(' ', '_').replace(':', '_')
        backup_path = os.path.join(backup_dir, safe_tgz_name)
        
        # Check if backup exists
        use_backup = False
        if os.path.isdir(backup_path):
            print(f"Found existing backup at {backup_path}")
            response = input("Use existing backup instead of extracting the .tgz file? (y/n): ").strip().lower()
            if response == 'y':
                use_backup = True
                # Copy backup to temp_extract_dir
                try:
                    shutil.copytree(backup_path, temp_extract_dir, dirs_exist_ok=True)
                    print(f"Using backup from {backup_path} in {temp_extract_dir}")
                except Exception as e:
                    print(f"Error copying backup from {backup_path}: {e}")
                    print("Falling back to extracting the .tgz file...")
                    use_backup = False
        
        # Extract the .tgz file if no backup is used
        if not use_backup:
            if not extract_tgz_file(tgz_path, temp_extract_dir):
                return False
        
        # Find kernel RPMs in extracted content or backup
        rpm_files = find_kernel_rpms(temp_extract_dir)
        if not rpm_files:
            return False
        
        # Get target kernel version before installation
        target_kernel_version = get_target_kernel_version(rpm_files)
        if target_kernel_version:
            print(f"Target kernel version: {target_kernel_version}")
        
        # Disable package excludes
        disable_package_excludes()
        
        # Install kernel packages
        install_success = install_kernel_rpms(rpm_files)
        
        # Restore package excludes
        restore_package_excludes()
        
        if install_success:
            print("\nKernel installation completed successfully!")
            print("Now setting the new kernel as default using kernel_commit...")
            
            # Wait a moment for the system to register the new kernel
            print("Waiting for system to register new kernel...")
            time.sleep(3)
            
            # Use kernel_commit script to set the default kernel
            commit_success = False
            if target_kernel_version:
                commit_success = run_kernel_commit_auto(target_kernel_version)
            else:
                commit_success = run_kernel_commit_interactive()
            
            # Copy the extracted folder to the user's home directory only if extracted
            if not use_backup:
                try:
                    os.makedirs(backup_dir, exist_ok=True)
                    # Remove existing backup if it exists to avoid conflicts
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path, ignore_errors=True)
                    shutil.copytree(temp_extract_dir, backup_path, dirs_exist_ok=True)
                    print(f"Extracted folder backed up to {backup_path}")
                except Exception as e:
                    print(f"Error backing up extracted folder to {backup_path}: {e}")
            
            if commit_success:
                print("\n" + "="*80)
                print("INSTALLATION COMPLETE!")
                print("="*80)
                print("? Kernel packages installed successfully")
                print("? Default kernel set successfully")
                print("? System ready for reboot")
                print("="*80)
                
                if auto_reboot:
                    print("Auto-rebooting system...")
                    subprocess.run(["sudo", "reboot"])
                else:
                    response = input("\nReboot now to use the new kernel? (y/n): ").strip().lower()
                    if response == 'y':
                        subprocess.run(["sudo", "reboot"])
                    else:
                        print("Don't forget to reboot to activate the new kernel!")
            else:
                print("\n" + "="*80)
                print("PARTIAL SUCCESS")
                print("="*80)
                print("? Kernel packages installed successfully")
                print("? Default kernel setting may need manual verification")
                print("You can run 'kernel_commit' manually to set the default kernel")
                print("="*80)
        
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
    5) Use kernel_commit.sh for reliable kernel default setting.
    6) Unmount share.
    """
    parser = argparse.ArgumentParser(
        description="NVM Burner & Kernel Installer - Flash images and install kernels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 nvm_tool.py                    # Interactive mode
  python3 nvm_tool.py --auto-reboot      # Auto-reboot after kernel install
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
                burn_image_to_ssd(chosen_file, disk_name)
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
