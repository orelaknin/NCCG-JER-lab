

#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import tempfile
import tarfile
import argparse
import shutil
import re
from glob import glob

def rerun_with_sudo():
    """
    Re-run the script with sudo if the current user is not root.
    """
    if os.geteuid() != 0:
        print("Re-running script with sudo...")
        try:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        except Exception as e:
            print(f" Failed to run with sudo: {e}")
            sys.exit(1)

rerun_with_sudo()


def check_and_install_pv():
    """
    Check if 'pv' (pipe viewer) is installed, and auto-install it if not.
    This is needed for progress monitoring during image burns.
    """
    try:
        # Check if pv is already installed
        result = subprocess.run(["which", "pv"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ pv (pipe viewer) is already installed")
            return True
        
        print("⚠ pv (pipe viewer) not found - required for progress monitoring")
        print("Installing pv automatically...")
        
        # Try different package managers
        install_commands = [
            ["sudo", "dnf", "install", "-y", "pv"],           # Fedora/RHEL
            ["sudo", "yum", "install", "-y", "pv"],           # CentOS/RHEL
            ["sudo", "apt", "install", "-y", "pv"],           # Ubuntu/Debian
            ["sudo", "zypper", "install", "-y", "pv"],        # openSUSE
            ["sudo", "pacman", "-S", "--noconfirm", "pv"],    # Arch Linux
        ]
        
        for cmd in install_commands:
            try:
                print(f"Trying: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("✓ pv installed successfully")
                    
                    # Verify installation
                    verify_result = subprocess.run(["which", "pv"], capture_output=True, text=True)
                    if verify_result.returncode == 0:
                        print(f"✓ pv verified at: {verify_result.stdout.strip()}")
                        return True
                    else:
                        print("⚠ pv installation succeeded but verification failed")
                        continue
                        
            except subprocess.TimeoutExpired:
                print(f"⚠ Installation command timed out: {' '.join(cmd)}")
                continue
            except Exception as e:
                print(f"⚠ Installation failed with {cmd[1]}: {e}")
                continue
        
        # If all package managers failed
        print("❌ Failed to install pv with any package manager")
        print("Please install pv manually:")
        print("  Fedora/RHEL: sudo dnf install pv")
        print("  Ubuntu/Debian: sudo apt install pv")
        print("  CentOS: sudo yum install pv")
        print("")
        print("The script will continue but progress monitoring may not work properly.")
        return False
        
    except Exception as e:
        print(f"❌ Error checking/installing pv: {e}")
        return False


# -----------------------------
# 1) MOUNT / UNMOUNT FUNCTIONS
# -----------------------------

def mount_remote_share(remote_path, mount_point, username=None, password=None):
    """
    Mounts a remote SMB share at the specified mount point.
    Checks if the share is already mounted before attempting to mount.
    """
    # Check if the remote share is already mounted at the mount point
    try:
        result = subprocess.run(
            ["findmnt", "-S", remote_path, "-M", mount_point],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"Remote share {remote_path} is already mounted at {mount_point}")
            return
    except subprocess.CalledProcessError:
        # findmnt returns non-zero if the mount point is not found
        pass
    except Exception as e:
        print(f"Error checking mount status: {e}")

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
    
    directory_contents = [item for item in os.listdir(directory_path) if item not in ("NVM", "mev_dual_imc_acc_connection.py")]
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
        elif item_name.lower().endswith(('.py','.sh')):
            file_type = "SCRIPT"
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

        print("\nOptions:")
        print("  [number] - Select item")
        print("  s        - Search for file by name")
        print("  q        - Quit")

        user_input = input("Enter your choice: ").strip()

        if user_input.lower() == 'q':
            return None
        elif user_input.lower() == 's':
            search_term = input("Enter search term: ").strip().lower()
            matches = [item for item in contents if search_term in item.lower()]
            if not matches:
                print("No matches found.")
                continue
            print("\nSearch results:")
            for idx, item_name in enumerate(matches, start=1):
                print(f"{idx}. {item_name}")
            sel = input("Select file by number or press Enter to cancel: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(matches):
                chosen_name = matches[int(sel) - 1]
                chosen_path = os.path.join(directory_path, chosen_name)
                if os.path.isdir(chosen_path):
                    directory_path = chosen_path
                else:
                    return chosen_path
            else:
                print("Cancelled or invalid selection.")
                continue
        else:
            try:
                choice = int(user_input)
                if 1 <= choice <= len(contents):
                    chosen_name = contents[choice - 1]
                    chosen_path = os.path.join(directory_path, chosen_name)
                    if os.path.isdir(chosen_path):
                        directory_path = chosen_path  # keep going deeper
                    else:
                        return chosen_path
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number, 's' to search, or 'q' to quit.")

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
            base_name = os.path.basename(rpm)
            full_version = re.match(r"kernel-(.+)", base_name).group(1).replace("_", "-")
            # Remove the suffix explicitly
            if re.match(r"^\d", full_version):
                # Remove the suffix '-1.x86-64.rpm' if present
                kernel_version = re.sub(r"-1\.x86-64\.rpm$", "", full_version)
            print(f"  - {os.path.basename(rpm)}")
        return found_rpms, kernel_version
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

    # Fetch available kernel titles from grubby
    grubby_titles = run_cmd("grubby --info=ALL | grep title= | grep -oP 'title=\"\\K[^\"]+' | sort")
    selected_title = None
    if grubby_titles:
        for line in grubby_titles.split('\n'):
            if target_kernel_version in line:
                selected_title = line
                break
    if not selected_title:
        print(f"\nCould not find a matching kernel title for version: {target_kernel_version}")
        print("Falling back to interactive commit mode...")
        return run_kernel_commit_interactive()

    print(f"\nCommitting kernel title: '{selected_title}'")

    response = input("\ncommit the new kernel? (y/n): ").strip().lower()
    if response == 'n':
        return None

    if update_grub_default(selected_title):
        rebuild_grub()
        print(f"\nKernel {selected_title} set as default successfully!")
        return True
    else:
        print(f"\nAutomatic kernel commit failed, falling back to interactive mode...")
        return run_kernel_commit_interactive()
            

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
        backup_dir = "/home/laduser"
        tgz_basename = os.path.splitext(os.path.basename(tgz_path))[0]
        safe_tgz_name = tgz_basename.replace(' ', '_').replace(':', '_')
        backup_path = os.path.join(backup_dir, safe_tgz_name)
        
        # Check if backup exists
        use_backup = False
        if os.path.isdir(backup_path):
            print(f"Found existing backup at {backup_path}")
            
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
            try:
                    os.makedirs(backup_dir, exist_ok=True)
                    # Remove existing backup if it exists to avoid conflicts
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path, ignore_errors=True)
                    shutil.copytree(temp_extract_dir, backup_path, dirs_exist_ok=True)
                    print(f"Extracted folder backed up to {backup_path}")
            except Exception as e:
                    print(f"Error backing up extracted folder to {backup_path}: {e}")
            run_cmd(f"sudo chmod 777 {backup_path}")

        
        # Find kernel RPMs in extracted content or backup
        rpm_files, kernel_version = find_kernel_rpms(temp_extract_dir)
        print(f"Hitting kernel version: {kernel_version}")
        if not rpm_files:
            return False

        # Fetch available kernel titles from grubby
        grubby_titles = run_cmd("grubby --info=ALL | grep title= | grep -oP 'title=\"\\K[^\"]+' | sort")
        selected_title = None
        if grubby_titles:
            for line in grubby_titles.split('\n'):
                if kernel_version in line:
                    selected_title = line
                    break

        if not selected_title:
            # Disable package excludes
            disable_package_excludes()
            
            # Install kernel packages
            install_success = install_kernel_rpms(rpm_files)
            
            # Restore package excludes
            restore_package_excludes()
        else:
            print("kernel is already installed, skipping installation.")
            install_success = True

        if install_success:
            print("\nKernel installation completed successfully!")
            print("Now setting the new kernel as default using kernel_commit...")
            
            # Wait a moment for the system to register the new kernel
            print("Waiting for system to register new kernel...")
            time.sleep(3)
            

            # Use kernel_commit script to set the default kernel
            commit_success = False
            if kernel_version:
                commit_success = run_kernel_commit_auto(kernel_version)
            else:
                commit_success = run_kernel_commit_interactive()
            
            # Copy the extracted folder to the user's home directory only if extracted
        
                
            
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
# 4) KERNEL commit 
# -------------------------

def run_cmd(cmd, get_output=True):
    result = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=get_output, text=True)
    return result.stdout.strip() if get_output else None

def get_boot_type():
    return "UEFI" if os.path.exists("/sys/firmware/efi") else "BIOS"

def progress_bar():
    print()
    print("Progress:")
    for progress in ['#####                     (33%)', '#############             (66%)', '#######################   (100%)']:
        print(progress, end='\r')
        time.sleep(1)
    print('\n')

def update_grub_default(selected_kernel):
    try:
        with open('/etc/default/grub', 'r') as file:
            lines = file.readlines()

        # Remove any existing GRUB_DEFAULT lines
        lines = [line for line in lines if not line.startswith('GRUB_DEFAULT=')]

        # Add the new GRUB_DEFAULT line
        lines.append(f'GRUB_DEFAULT="{selected_kernel}"\n')

        with open('/etc/default/grub', 'w') as file:
            file.writelines(lines)

        return True  # Success

    except Exception as e:
        print(f"Failed to update /etc/default/grub: {e}")
        return False  # Failure


def rebuild_grub():
    print("\nRebuilding GRUB config...")
    efi_partition = run_cmd("fdisk -l | grep -i 'fat\\|efi' | awk '{print $1}'")

    os.makedirs('/mnt/efi_kernel', exist_ok=True)
    run_cmd(f"mount {efi_partition} /mnt/efi_kernel", get_output=False)

    run_cmd("grub2-mkconfig -o /mnt/efi_kernel/EFI/fedora/grub.cfg", get_output=False)
    run_cmd("grub2-mkconfig -o /boot/grub2/grub.cfg", get_output=False)

    progress_bar()
    print("\n\033[01;32m The kernel pointers are in place. Please reboot your host to commit this action. \033[0m\n")

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

def copy_ssh_config_to_root():
    """
    Copy the user's SSH config file to the root user's SSH config location.
    Creates the root .ssh directory if it does not exist.
    """
    user_ssh_config = '/home/laduser/.ssh/config'
    root_ssh_dir = '/root/.ssh'
    root_ssh_config = os.path.join(root_ssh_dir, 'config')
    try:
        if not os.path.exists(user_ssh_config):
            print(f"User SSH config not found: {user_ssh_config}")
            return False
        os.makedirs(root_ssh_dir, exist_ok=True)
        shutil.copy2(user_ssh_config, root_ssh_config)
        print(f"Copied SSH config to {root_ssh_config}")
        return True
    except Exception as e:
        print(f"Error copying SSH config to root: {e}")
        return False

def list_imc_ssh_connections(ssh_config_path=None):
    """
    Reads the SSH config file and lists all Host entries starting with 'IMC'.
    Returns a list of hostnames (e.g., IMC1, IMC2, ...).
    """
    # Always use the real user's SSH config, not root's
    ssh_config_path = '/home/laduser/.ssh/config'
    if not os.path.exists(ssh_config_path):
        print(f"SSH config file not found: {ssh_config_path}")
        return []

    imc_hosts = []
    with open(ssh_config_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Match lines like: Host IMC1, Host IMC2, etc.
            m = re.match(r'^Host\s+(IMC\S*)', line)
            if m:
                imc_hosts.append(m.group(1))
    return imc_hosts

def burn_image_to_imc(image_file):
    """
    List IMC SSH connections, prompt user to select one, then burn image to it.
    """
    import tempfile
    
    # Check and install pv when user chooses to burn to IMC
    print("Checking for required tools...")
    check_and_install_pv()
    
    imc_list = list_imc_ssh_connections()
    print(f"imc_list: {imc_list}")
    if not imc_list:
        print("No IMC connections found in SSH config. please use IMC_ACC_CONNECTION script to set up IMC connections.")
        return
    print("\nAvailable IMC connections:")
    copy_ssh_config_to_root()
    for idx, imc in enumerate(imc_list, 1):
        print(f"  {idx}. {imc}")
    while True:
        choice = input("Select IMC number to burn image to (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            print("Aborted.")
            return
        if choice.isdigit() and 1 <= int(choice) <= len(imc_list):
            selected_imc = imc_list[int(choice)-1]
            print(f"Selected IMC: {selected_imc}")
            break
        else:
            print("Invalid selection. Try again.")

    # Copy image file to /tmp with a unique name
    tmp_dir = tempfile.gettempdir()
    local_tmp_image = os.path.join(tmp_dir, os.path.basename(image_file))
    try:
        print(f"Copying image file to temporary location: {local_tmp_image}")
        shutil.copy2(image_file, local_tmp_image)
    except Exception as e:
        print(f"Failed to copy image to /tmp: {e}")
        return

    try:
        print(f"\nSetting syslog mode on {selected_imc} ...")
        cmd1 = ["ssh", selected_imc, "/etc/init.d/syslogmode DEV"]
        subprocess.run(cmd1)

        print(f"\nBurning image {local_tmp_image} to {selected_imc}:/dev/nvme0n1 ...")
        
        # Check if pv is available for progress monitoring
        pv_available = subprocess.run(["which", "pv"], capture_output=True, text=True).returncode == 0
        
        if pv_available:
            print("Using pv for progress monitoring...")
            cmd2 = f"(pv -fB 512M -f '{local_tmp_image}' | ssh {selected_imc} 'dd of=/dev/nvme0n1 bs=512M') |& stdbuf -oL tr '\r' '\n'"
        else:
            print("pv not available - using dd without progress monitoring...")
            cmd2 = f"dd if='{local_tmp_image}' bs=512M | ssh {selected_imc} 'dd of=/dev/nvme0n1 bs=512M'"
        
        subprocess.run(cmd2, shell=True)
        print("\nImage burn process completed.")
    finally:
        print("Cleaning up temporary files...")
        # Remove the temporary image file
       # try:
        
        #    if os.path.exists(local_tmp_image):
        #        os.remove(local_tmp_image)
          #      print(f"Temporary image file {local_tmp_image} deleted.")
       # except Exception as e:
         #   print(f"Failed to delete temporary image file: {e}")

# --------------------------
# 6) MAIN SCRIPT / WORKFLOW
# --------------------------

def main():
    """
    Enhanced main function that can:
    1) Mount remote share to a temp dir, checking if already mounted.
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

    elif file_extension == '.py':
        print(f"\nDetected script file: {os.path.basename(chosen_file)}")
        try:
            subprocess.run([sys.executable, chosen_file], check=True)
        except Exception as e:
            print(f"Error running script: {e}")
        else:
            print("Skipping script execution")

    elif file_extension == '.sh':
        print(f"\nDetected bash script: {os.path.basename(chosen_file)}")
        if os.path.basename(chosen_file) == "ATS.sh":
            while True:
                param = input("Choose parameter for ATS.sh ('on' or 'off'): ").strip().lower()
                if param in ['on', 'off']:
                    break
                else:
                    print("Invalid input. Please enter 'on' or 'off'.")
            try:
                subprocess.run(['bash', chosen_file, param], check=True)
            except Exception as e:
                print(f"Error running ATS.sh: {e}")
        else:
            response = input("Do you want to execute this bash script? (y/n): ").strip().lower()
            if response == 'y':
                try:
                    subprocess.run(['bash', chosen_file], check=True)
                except Exception as e:
                    print(f"Error running script: {e}")
            else:
                print("Skipping script execution")

    elif file_extension in ['.img', '.iso', '.bin', '.raw'] or os.path.isfile(chosen_file):
        print(f"\nDetected image file: {os.path.basename(chosen_file)}")
        response = input("Do you want to burn this image to MMG directly? (y/n): ").strip().lower()
        if response == 'y':
            burn_image_to_imc(chosen_file)
        else:
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