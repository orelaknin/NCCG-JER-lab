#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import tempfile
import tarfile
import shutil
from glob import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread
from time import ctime

# -----------------------------
# 1) MOUNT / UNMOUNT FUNCTIONS
# -----------------------------

def mount_remote_share(remote_path, mount_point, username=None, password=None):
    """
    Mounts a remote SMB share at the specified mount point.
    """
    if not os.path.exists(mount_point):
        os.makedirs(mount_point)
    
    mount_cmd = ["sudo", "mount", "-t", "cifs", remote_path, mount_point]
    
    options = []
    if username and password:
        options.append(f"username={username}")
        options.append(f"password={password}")
    options.append("vers=3.0")  # Removed the invalid '?' and added as a valid option
    
    if options:
        mount_cmd.extend(["-o", ",".join(options)])  # Combine options into a single -o argument
    
    try:
        subprocess.run(mount_cmd, check=True, capture_output=True, text=True)
        return True, f"Successfully mounted {remote_path} at {mount_point}"
    except subprocess.CalledProcessError as e:
        return False, f"Mount failed: {e.stderr}"

def unmount_share(mount_point):
    """
    Safely unmount the share and clean up.
    """
    os.chdir("/")
    try:
        subprocess.run(["sudo", "umount", mount_point], check=True)
        os.rmdir(mount_point)
        return True, f"Share successfully unmounted: {mount_point}"
    except Exception as e:
        return False, f"Error unmounting share {mount_point}: {e}"

# -----------------------------
# 2) DETECT SSD
# -----------------------------

def check_disk_exists(disk_name):
    """
    Checks if the given disk name is detected by the system (fdisk).
    """
    check_disk = subprocess.run(["fdisk", "-l"], capture_output=True, text=True)
    
    if check_disk.returncode == 0:
        if disk_name in check_disk.stdout:
            return True, f"NVMe is detected! ({disk_name})"
        else:
            return False, f"NVMe {disk_name} is not detected! Note: You can still use kernel installation features."
    else:
        return False, "Error running fdisk -l"

# -------------------------
# 3) KERNEL MANAGEMENT
# -------------------------

def check_uefi_mode():
    """
    Check if system is running in UEFI mode.
    """
    if os.path.exists("/sys/firmware/efi"):
        return True, "System is running in UEFI mode"
    else:
        return False, "System is running in Legacy BIOS mode\nThis script currently only supports UEFI mode"

def extract_tgz_file(tgz_path, extract_dir):
    """
    Extract a .tgz file to the specified directory.
    """
    try:
        output = [f"Extracting {os.path.basename(tgz_path)}..."]
        try:
            result = subprocess.run(
                ["tar", "-xvf", tgz_path, "-C", extract_dir],
                capture_output=True, text=True, check=True
            )
            output.append(f"Extraction completed to {extract_dir}")
            output.append("Files extracted:")
            for line in result.stdout.split('\n')[:5]:
                if line.strip():
                    output.append(f"  - {line.strip()}")
            return True, "\n".join(output)
        except subprocess.CalledProcessError as e:
            output.append(f"Simple tar failed: {e}")
        try:
            result = subprocess.run(
                ["tar", "-xzvf", tgz_path, "-C", extract_dir],
                capture_output=True, text=True, check=True
            )
            output.append(f"Extraction completed to {extract_dir}")
            return True, "\n".join(output)
        except subprocess.CalledProcessError as e:
            output.append(f"Gzip tar failed: {e}")
        try:
            with tarfile.open(tgz_path, 'r:') as tar:
                tar.extractall(extract_dir)
            output.append(f"Extraction completed to {extract_dir}")
            return True, "\n".join(output)
        except Exception as e:
            output.append(f"Python tarfile failed: {e}")
        try:
            file_result = subprocess.run(['file', tgz_path], capture_output=True, text=True)
            output.append(f"File type detection: {file_result.stdout.strip()}")
        except:
            pass
        output.append("All extraction methods failed")
        return False, "\n".join(output)
    except Exception as e:
        return False, f"Error extracting file: {e}"

def find_kernel_rpms(directory):
    """
    Find kernel RPM files in the given directory (recursively).
    """
    kernel_types = ['kernel-[0-9]*.rpm', 'kernel-devel*.rpm', 'kernel-headers*.rpm', 
                    'kernel-modules*.rpm', 'kernel-core*.rpm']
    found_rpms = []
    for root, dirs, files in os.walk(directory):
        for kernel_pattern in kernel_types:
            matches = glob(os.path.join(root, kernel_pattern))
            found_rpms.extend(matches)
    if found_rpms:
        output = [f"Found {len(found_rpms)} kernel RPM files:"]
        for rpm in found_rpms:
            output.append(f"  - {os.path.basename(rpm)}")
        return found_rpms, "\n".join(output)
    else:
        return [], f"No kernel RPM files found in {directory}"

def disable_package_excludes():
    """
    Temporarily disable kernel excludes in DNF/YUM config.
    """
    try:
        if os.path.exists("/etc/dnf/dnf.conf"):
            subprocess.run(["sudo", "chattr", "-ia", "/etc/dnf/dnf.conf"], check=True)
            subprocess.run(["sudo", "sed", "-e", "/exclude/ s/^#*/#/", "-i", "/etc/dnf/dnf.conf"], check=True)
        if os.path.exists("/etc/yum.conf"):
            subprocess.run(["sudo", "sed", "-e", "/exclude/ s/^#*/#/", "-i", "/etc/yum.conf"], check=True)
        return True, "Package excludes temporarily disabled"
    except Exception as e:
        return False, f"Error disabling package excludes: {e}"

def restore_package_excludes():
    """
    Restore kernel excludes in DNF/YUM config.
    """
    try:
        if os.path.exists("/etc/dnf/dnf.conf"):
            subprocess.run(["sudo", "sed", "-i", "s/#exclude/exclude/g", "/etc/dnf/dnf.conf"], check=True)
            subprocess.run(["sudo", "chattr", "+ia", "/etc/dnf/dnf.conf"], check=True)
        if os.path.exists("/etc/yum.conf"):
            subprocess.run(["sudo", "sed", "-i", "s/#exclude/exclude/g", "/etc/yum.conf"], check=True)
        return True, "Package excludes restored"
    except Exception as e:
        return False, f"Error restoring package excludes: {e}"

def install_kernel_rpms(rpm_files):
    """
    Install kernel RPM files using DNF.
    """
    output = [f"Installing {len(rpm_files)} kernel packages..."]
    success_count = 0
    for rpm_file in rpm_files:
        try:
            output.append(f"Installing {os.path.basename(rpm_file)}...")
            result = subprocess.run(
                ["sudo", "dnf", "-y", "localinstall", rpm_file, "--allowerasing"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                output.append(f"  {os.path.basename(rpm_file)} installed successfully")
                success_count += 1
            else:
                output.append(f"  Failed to install {os.path.basename(rpm_file)}")
                output.append(f"  Error: {result.stderr}")
        except Exception as e:
            output.append(f"  Error installing {os.path.basename(rpm_file)}: {e}")
    output.append(f"Installation summary: {success_count}/{len(rpm_files)} packages installed successfully")
    return success_count > 0, "\n".join(output)

def get_target_kernel_version(rpm_files):
    """
    Extract the target kernel version from the main kernel RPM file.
    """
    main_kernel_rpm = None
    for rpm_file in rpm_files:
        rpm_basename = os.path.basename(rpm_file)
        if rpm_basename.startswith('kernel-') and not any(x in rpm_basename for x in ['devel', 'headers', 'modules', 'core']):
            main_kernel_rpm = rpm_basename
            break
    if main_kernel_rpm:
        name_without_ext = main_kernel_rpm.replace('.rpm', '')
        version_part = name_without_ext[7:]
        if '-' in version_part:
            parts = version_part.split('-')
            if len(parts) >= 2:
                kernel_version = '-'.join(parts[:-1]).replace('_', '-')
                return kernel_version
    return None

def run_kernel_commit_interactive():
    """
    Run the kernel_commit.sh script interactively (not used in GUI).
    """
    output = ["="*80, "KERNEL COMMIT - Setting Default Kernel", "="*80]
    output.append("The kernel_commit script is not supported in GUI mode.")
    output.append("Please run 'kernel_commit' manually to set the default kernel.")
    output.append("="*80)
    return False, "\n".join(output)

def run_kernel_commit_auto(target_kernel_version):
    """
    Automatically select the target kernel in kernel_commit script.
    """
    output = ["="*80, "KERNEL COMMIT - Setting Default Kernel", "="*80]
    output.append(f"Attempting to automatically set kernel: {target_kernel_version}")
    output.append("="*80)
    
    kernel_commit_paths = [
        "/net/inx028core.intel.com/data/things/scripts/kernel_commit.sh",
        "./kernel_commit.sh",
        "/usr/local/bin/kernel_commit.sh",
        "/opt/scripts/kernel_commit.sh",
    ]
    
    kernel_commit_cmd = None
    try:
        result = subprocess.run(
            ["bash", "-c", "type kernel_commit"], 
            capture_output=True, text=True
        )
        if result.returncode == 0 and "alias" in result.stdout:
            output.append("Found kernel_commit alias")
            kernel_commit_cmd = ["bash", "-c", "kernel_commit"]
        else:
            output.append("kernel_commit alias not found, trying direct paths...")
    except:
        pass
    
    if not kernel_commit_cmd:
        for path in kernel_commit_paths:
            if os.path.exists(path):
                output.append(f"Found kernel_commit script at: {path}")
                kernel_commit_cmd = ["sudo", "bash", path]
                break
    
    if not kernel_commit_cmd:
        output.append("Error: kernel_commit script not found in any of these locations:")
        for path in kernel_commit_paths:
            output.append(f"  - {path}")
        output.append("Please run 'kernel_commit' manually to set the default kernel")
        return False, "\n".join(output)
    
    try:
        grubby_result = subprocess.run([
            "bash", "-c", 
            "grubby --info=ALL | grep title= | grep -oP 'title=\"\\K[^\"]+'"
        ], capture_output=True, text=True)
        
        if grubby_result.returncode != 0:
            output.append("Could not get kernel list")
            output.append("Please run 'kernel_commit' manually to set the default kernel")
            return False, "\n".join(output)
        
        kernel_titles = [line.strip() for line in grubby_result.stdout.split('\n') if line.strip()]
        target_index = None
        
        for i, title in enumerate(kernel_titles, 1):
            if target_kernel_version in title:
                target_index = i
                output.append(f"Found target kernel at index {target_index}: {title}")
                break
        
        if target_index is None:
            output.append(f"Could not find kernel {target_kernel_version} in available kernels")
            output.append("Please run 'kernel_commit' manually to set the default kernel")
            return False, "\n".join(output)
        
        output.append(f"Automatically selecting kernel option {target_index}...")
        process = subprocess.run(
            kernel_commit_cmd,
            input=f"{target_index}\n",
            text=True,
            capture_output=True
        )
        output.append("kernel_commit output:")
        output.append(process.stdout)
        
        if process.returncode == 0:
            output.append(f"Kernel {target_kernel_version} set as default successfully!")
            return True, "\n".join(output)
        else:
            output.append(f"Automatic kernel commit failed with return code: {process.returncode}")
            output.append("Please run 'kernel_commit' manually to set the default kernel")
            return False, "\n".join(output)
    except Exception as e:
        output.append(f"Error in automatic kernel commit: {e}")
        output.append("Please run 'kernel_commit' manually to set the default kernel")
        return False, "\n".join(output)

def install_kernel_from_tgz(tgz_path, auto_reboot, text_area):
    """
    Complete workflow to install kernel from a .tgz file, updated for GUI.
    """
    def update_text_area(message):
        text_area.insert(tk.END, message + "\n")
        text_area.see(tk.END)
        text_area.update()

    update_text_area(f"Starting kernel installation from {os.path.basename(tgz_path)}")
    
    success, message = check_uefi_mode()
    update_text_area(message)
    if not success:
        return False
    
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
            update_text_area(f"Found existing backup at {backup_path}")
            result = messagebox.askyesno("Use Backup", f"Use existing backup at {backup_path} instead of extracting the .tgz file?")
            if result:
                use_backup = True
                try:
                    shutil.copytree(backup_path, temp_extract_dir, dirs_exist_ok=True)
                    update_text_area(f"Using backup from {backup_path} in {temp_extract_dir}")
                except Exception as e:
                    update_text_area(f"Error copying backup from {backup_path}: {e}")
                    update_text_area("Falling back to extracting the .tgz file...")
                    use_backup = False
        
        # Extract the .tgz file if no backup is used
        if not use_backup:
            success, message = extract_tgz_file(tgz_path, temp_extract_dir)
            update_text_area(message)
            if not success:
                return False
        
        # Find kernel RPMs in extracted content or backup
        rpm_files, message = find_kernel_rpms(temp_extract_dir)
        update_text_area(message)
        if not rpm_files:
            return False
        
        # Get target kernel version before installation
        target_kernel_version = get_target_kernel_version(rpm_files)
        if target_kernel_version:
            update_text_area(f"Target kernel version: {target_kernel_version}")
        
        # Disable package excludes
        success, message = disable_package_excludes()
        update_text_area(message)
        
        # Install kernel packages
        install_success, message = install_kernel_rpms(rpm_files)
        update_text_area(message)
        
        # Restore package excludes
        success, message = restore_package_excludes()
        update_text_area(message)
        
        if install_success:
            update_text_area("Kernel installation completed successfully!")
            update_text_area("Now setting the new kernel as default using kernel_commit...")
            update_text_area("Waiting for system to register new kernel...")
            time.sleep(3)
            
            # Use kernel_commit script to set the default kernel
            commit_success = False
            if target_kernel_version:
                commit_success, message = run_kernel_commit_auto(target_kernel_version)
                update_text_area(message)
            else:
                commit_success, message = run_kernel_commit_interactive()
                update_text_area(message)
            
            # Copy the extracted folder to the user's home directory only if extracted
            if not use_backup:
                try:
                    os.makedirs(backup_dir, exist_ok=True)
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path, ignore_errors=True)
                    shutil.copytree(temp_extract_dir, backup_path, dirs_exist_ok=True)
                    update_text_area(f"Extracted folder backed up to {backup_path}")
                except Exception as e:
                    update_text_area(f"Error backing up extracted folder to {backup_path}: {e}")
            
            if commit_success:
                update_text_area("\n" + "="*80)
                update_text_area("INSTALLATION COMPLETE!")
                update_text_area("="*80)
                update_text_area("? Kernel packages installed successfully")
                update_text_area("? Default kernel set successfully")
                update_text_area("? System ready for reboot")
                update_text_area("="*80)
                
                if auto_reboot:
                    update_text_area("Auto-rebooting system...")
                    subprocess.run(["sudo", "reboot"])
                else:
                    result = messagebox.askyesno("Reboot", "Reboot now to use the new kernel?")
                    if result:
                        update_text_area("Rebooting system...")
                        subprocess.run(["sudo", "reboot"])
                    else:
                        update_text_area("Don't forget to reboot to activate the new kernel!")
            else:
                update_text_area("\n" + "="*80)
                update_text_area("PARTIAL SUCCESS")
                update_text_area("="*80)
                update_text_area("? Kernel packages installed successfully")
                update_text_area("? Default kernel setting may need manual verification")
                update_text_area("You can run 'kernel_commit' manually to set the default kernel")
                update_text_area("="*80)
        
        return install_success
        
    finally:
        shutil.rmtree(temp_extract_dir, ignore_errors=True)

# -------------------------
# 4) BURN IMAGE
# -------------------------

def burn_image_to_ssd(image_path, disk_name="/dev/nvme0n1", text_area=None):
    """
    Uses dd to copy the given file to the NVMe device.
    """
    def update_text_area(message):
        if text_area:
            text_area.insert(tk.END, message + "\n")
            text_area.see(tk.END)
            text_area.update()

    if not os.path.isfile(image_path):
        update_text_area(f"Error: '{image_path}' is not a file.")
        return False
    
    update_text_area(f"Burning {image_path} to {disk_name} ...")
    try:
        result = subprocess.run(
            ["sudo", "dd", f"if={image_path}", f"of={disk_name}", "status=progress"],
            capture_output=True, text=True
        )
        update_text_area("Burn process completed.")
        return True
    except Exception as e:
        update_text_area(f"Error burning image: {e}")
        return False

# --------------------------
# 5) GUI
# --------------------------

class NVMToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NVM Burner & Kernel Installer")
        self.root.geometry("800x600")
        self.remote_path = "//ladjsvop.jer.intel.com/burn"
        self.mount_dir = os.path.join(tempfile.gettempdir(), "remote_burn_mount")
        self.disk_name = "/dev/nvme0n1"
        self.username = "laduser"
        self.password = "$giga"
        self.is_mounted = False
        self.current_dir = self.mount_dir

        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Home frame
        self.home_frame = ttk.Frame(self.root, padding="10")
        self.home_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.home_frame.columnconfigure(0, weight=1)  # Left column
        self.home_frame.columnconfigure(1, weight=1)  # Right column
        self.home_frame.rowconfigure(4, weight=1)     # Allow status bar row to push down

        # Home page title
        ttk.Label(self.home_frame, text="OPS Tools", font=("Arial", 16, "bold"), anchor=tk.CENTER).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)

        # Home page buttons (two centered columns)
        self.kernel_button = ttk.Button(self.home_frame, text="Kernel", command=self.show_kernel_frame)
        self.kernel_button.grid(row=1, column=0, padx=10, pady=5, sticky=(tk.E, tk.W))

        self.nvm_button = ttk.Button(self.home_frame, text="NVM", command=self.show_nvm_frame)
        self.nvm_button.grid(row=1, column=1, padx=10, pady=5, sticky=(tk.E, tk.W))

        self.ssd_button = ttk.Button(self.home_frame, text="SSD", command=self.show_ssd_frame)
        self.ssd_button.grid(row=2, column=0, padx=10, pady=5, sticky=(tk.E, tk.W))

        self.extra1_button = ttk.Button(self.home_frame, text="Extra 1", command=self.show_extra1_frame)
        self.extra1_button.grid(row=3, column=0, padx=10, pady=5, sticky=(tk.E, tk.W))

        self.extra2_button = ttk.Button(self.home_frame, text="Extra 2", command=self.show_extra2_frame)
        self.extra2_button.grid(row=2, column=1, padx=10, pady=5, sticky=(tk.E, tk.W))

        # Status bar
        self.status_bar = ttk.Label(self.home_frame, text="Status: Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Kernel frame (new page for kernel directory contents)
        self.kernel_frame = ttk.Frame(self.root, padding="10")
        self.kernel_status = ttk.Label(self.kernel_frame, text="Kernel Directory Contents")
        self.kernel_status.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Kernel options listbox
        self.kernel_listbox = tk.Listbox(self.kernel_frame, height=10, width=80)
        self.kernel_listbox.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.kernel_listbox.bind('<<ListboxSelect>>', self.on_kernel_option_select)

        # Buttons
        self.proceed_button = ttk.Button(self.kernel_frame, text="Proceed to File Selection", command=self.show_main_frame, state=tk.DISABLED)
        self.proceed_button.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.back_to_home_button = ttk.Button(self.kernel_frame, text="Back", command=self.go_back_to_home)
        self.back_to_home_button.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # Output text area
        self.kernel_text_area = tk.Text(self.kernel_frame, height=15, width=80, state='normal')
        self.kernel_text_area.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.kernel_frame.columnconfigure(0, weight=1)
        self.kernel_frame.rowconfigure(3, weight=1)

        # Main frame (original file selection and installation)
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.mount_status = ttk.Label(self.main_frame, text="Mounting...")
        self.mount_status.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        self.select_file_button = ttk.Button(self.main_frame, text="Select File", command=self.select_file, state=tk.DISABLED)
        self.select_file_button.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.install_button = ttk.Button(self.main_frame, text="Install Kernel", command=self.install_kernel, state=tk.DISABLED)
        self.install_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.burn_button = ttk.Button(self.main_frame, text="Burn Image", command=self.burn_image, state=tk.DISABLED)
        self.burn_button.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        self.back_button = ttk.Button(self.main_frame, text="Back to Kernel Options", command=self.show_kernel_frame)
        self.back_button.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.unmount_button = ttk.Button(self.main_frame, text="Unmount & Exit", command=self.unmount_and_exit)
        self.unmount_button.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)

        self.file_listbox = tk.Listbox(self.main_frame, height=10, width=80)
        self.file_listbox.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        self.auto_reboot_var = tk.BooleanVar()
        self.auto_reboot_check = ttk.Checkbutton(
            self.main_frame, text="Auto-reboot after kernel install", variable=self.auto_reboot_var
        )
        self.auto_reboot_check.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        self.text_area = tk.Text(self.main_frame, height=15, width=80, state='normal')
        self.text_area.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(5, weight=1)

        # Placeholder frames
        self.nvm_frame = ttk.Frame(self.root, padding="10")
        ttk.Label(self.nvm_frame, text="NVM Functionality (To be implemented)").grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(self.nvm_frame, text="Back", command=self.go_back_to_home).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.ssd_frame = ttk.Frame(self.root, padding="10")
        ttk.Label(self.ssd_frame, text="SSD Functionality (To be implemented)").grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(self.ssd_frame, text="Back", command=self.go_back_to_home).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.extra1_frame = ttk.Frame(self.root, padding="10")
        ttk.Label(self.extra1_frame, text="Extra 1 Functionality (To be implemented)").grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(self.extra1_frame, text="Back", command=self.go_back_to_home).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.extra2_frame = ttk.Frame(self.root, padding="10")
        ttk.Label(self.extra2_frame, text="Extra 1 Functionality (To be implemented)").grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(self.extra2_frame, text="Back", command=self.go_back_to_home).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        # Initialize
        self.selected_file = None
        self.selected_kernel_item = None
        self.dir_history = [self.mount_dir]
        self.current_frame = self.home_frame
        self.check_disk()
        self.mount_share()
        self.populate_kernel_list()

    def update_text_area(self, message, text_widget=None):
        text_area = text_widget or self.text_area
        text_area.insert(tk.END, message + "\n")
        text_area.see(tk.END)
        text_area.update()

    def check_disk(self):
        success, message = check_disk_exists(self.disk_name)
        self.update_text_area(message, self.text_area)
        self.burn_button.config(state=tk.NORMAL if success else tk.DISABLED)

    def mount_share(self):
        self.update_text_area(f"Checking if {self.remote_path} is mounted at {self.mount_dir}...", self.text_area)
        mount_output = subprocess.run(["mount"], capture_output=True, text=True).stdout
        if self.mount_dir in mount_output:
            self.update_text_area(f"{self.mount_dir} is already mounted. Skipping remount.", self.text_area)
            self.is_mounted = True
            self.mount_status.config(text=f"Mounted: {self.remote_path}")
            self.select_file_button.config(state=tk.NORMAL)
            self.populate_file_list()
        else:
            self.update_text_area(f"Attempting to mount {self.remote_path} to {self.mount_dir}...", self.text_area)
            success, message = mount_remote_share(self.remote_path, self.mount_dir, self.username, self.password)
            self.update_text_area(message, self.text_area)
            if success:
                self.is_mounted = True
                self.mount_status.config(text=f"Mounted: {self.remote_path}")
                self.select_file_button.config(state=tk.NORMAL)
                self.populate_file_list()
            else:
                messagebox.showerror("Mount Error", message)
                self.root.quit()

    def unmount_and_exit(self):
        if self.is_mounted:
            success, message = unmount_share(self.mount_dir)
            self.update_text_area(message, self.text_area)
        self.root.quit()

    def populate_file_list(self):
        self.file_listbox.delete(0, tk.END)
        if not os.path.isdir(self.current_dir):
            self.update_text_area(f"Error: Directory '{self.current_dir}' does not exist.", self.text_area)
            return
        contents = os.listdir(self.current_dir)
        contents.sort()
        self.update_text_area(f"Contents of: {self.current_dir}", self.text_area)
        for item in contents:
            full_path = os.path.join(self.current_dir, item)
            file_type = "DIR" if os.path.isdir(full_path) else \
                        "KERNEL" if item.lower().endswith(('.tgz', '.tar.gz')) else \
                        "IMAGE" if item.lower().endswith(('.img', '.iso', '.bin', '.raw')) else "FILE"
            self.file_listbox.insert(tk.END, f"{item} ({file_type})")

    def populate_kernel_list(self):
        self.kernel_listbox.delete(0, tk.END)
        kernel_dir = os.path.join(self.mount_dir, "Kernel")
        if not os.path.isdir(kernel_dir):
            self.update_text_area(f"Error: Directory '{kernel_dir}' does not exist.", self.kernel_text_area)
            return
        contents = os.listdir(kernel_dir)
        contents.sort()
        self.update_text_area(f"Contents of: {kernel_dir}", self.kernel_text_area)
        for item in contents:
            full_path = os.path.join(kernel_dir, item)
            creation_time = ctime(os.path.getctime(full_path))
            file_type = "DIR" if os.path.isdir(full_path) else "KERNE"  # Simplified type matching CLI
            self.kernel_listbox.insert(tk.END, f"{item} - {creation_time} {file_type}")

    def go_back(self):
        if len(self.dir_history) > 1:
            self.dir_history.pop()
            self.current_dir = self.dir_history[-1]
            self.populate_file_list()
            if len(self.dir_history) == 1:
                self.back_button.config(state=tk.DISABLED)

    def go_back_to_home(self):
        self.current_frame.grid_remove()
        self.home_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.home_frame

    def show_kernel_frame(self):
        self.current_frame.grid_remove()
        self.kernel_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.kernel_frame
        self.populate_kernel_list()  # Refresh list when showing frame

    def show_main_frame(self):
        self.current_frame.grid_remove()
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.main_frame

    def show_nvm_frame(self):
        self.current_frame.grid_remove()
        self.nvm_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.nvm_frame

    def show_ssd_frame(self):
        self.current_frame.grid_remove()
        self.ssd_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.ssd_frame

    def show_extra1_frame(self):
        self.current_frame.grid_remove()
        self.extra1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.extra1_frame

    def show_extra2_frame(self):
        self.current_frame.grid_remove()
        self.extra2_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame = self.extra2_frame

    def on_kernel_option_select(self, event):
        selection = self.kernel_listbox.curselection()
        if not selection:
            return
        selected_item = self.kernel_listbox.get(selection[0]).split(' - ')[0]  # Extract item name
        self.selected_kernel_item = os.path.join(self.mount_dir, "Kernel", selected_item)
        self.update_text_area(f"Selected: {selected_item}", self.kernel_text_area)
        self.proceed_button.config(state=tk.NORMAL if os.path.isfile(self.selected_kernel_item) else tk.DISABLED)

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return
        selected_item = self.file_listbox.get(selection[0]).split(' (')[0]
        selected_path = os.path.join(self.current_dir, selected_item)
        if os.path.isdir(selected_path):
            self.current_dir = selected_path
            self.dir_history.append(self.current_dir)
            self.back_button.config(state=tk.NORMAL)
            self.populate_file_list()
        else:
            self.selected_file = selected_path
            self.select_file_button.config(state=tk.DISABLED)
            self.install_button.config(state=tk.NORMAL if selected_path.lower().endswith(('.tgz', '.tar.gz')) else tk.DISABLED)
            self.burn_button.config(state=tk.NORMAL if selected_path.lower().endswith(('.img', '.iso', '.bin', '.raw')) else tk.DISABLED)

    def select_file(self):
        initial_dir = self.current_dir if os.path.isdir(self.current_dir) else os.path.expanduser("~/")
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("Kernel/Image files", "*.tgz *.tar.gz *.img *.iso *.bin *.raw"), ("All files", "*.*")]
        )
        if file_path:
            self.selected_file = file_path
            self.file_listbox.delete(0, tk.END)
            self.file_listbox.insert(tk.END, f"{os.path.basename(file_path)} (SELECTED)")
            self.select_file_button.config(state=tk.DISABLED)
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_path.lower().endswith(('.tgz', '.tar.gz')):
                self.install_button.config(state=tk.NORMAL)
            if file_path.lower().endswith(('.img', '.iso', '.bin', '.raw')):
                self.burn_button.config(state=tk.NORMAL)

    def install_kernel(self):
        if not self.selected_file:
            messagebox.showerror("Error", "No file selected for kernel installation.")
            return
        self.install_button.config(state=tk.DISABLED)
        self.burn_button.config(state=tk.DISABLED)
        self.select_file_button.config(state=tk.DISABLED)
        Thread(target=self.run_install_kernel, daemon=True).start()

    def run_install_kernel(self):
        install_kernel_from_tgz(self.selected_file, self.auto_reboot_var.get(), self.text_area)
        self.install_button.config(state=tk.DISABLED if not self.selected_file else tk.NORMAL)
        self.burn_button.config(state=tk.DISABLED if not self.selected_file else tk.NORMAL)
        self.select_file_button.config(state=tk.NORMAL)

    def burn_image(self):
        if not self.selected_file:
            messagebox.showerror("Error", "No file selected for burning.")
            return
        result = messagebox.askyesno("Confirm", f"Burn {os.path.basename(self.selected_file)} to {self.disk_name}?")
        if not result:
            self.update_text_area("Burn operation cancelled.", self.text_area)
            return
        self.install_button.config(state=tk.DISABLED)
        self.burn_button.config(state=tk.DISABLED)
        self.select_file_button.config(state=tk.DISABLED)
        Thread(target=self.run_burn_image, daemon=True).start()

    def run_burn_image(self):
        burn_image_to_ssd(self.selected_file, self.disk_name, self.text_area)
        self.install_button.config(state=tk.DISABLED if not self.selected_file else tk.NORMAL)
        self.burn_button.config(state=tk.DISABLED if not self.selected_file else tk.NORMAL)
        self.select_file_button.config(state=tk.NORMAL)

# Note: The following functions are assumed to be defined elsewhere
# def check_disk_exists(disk_name): ...
# def mount_remote_share(remote_path, mount_dir, username, password): ...
# def unmount_share(mount_dir): ...
# def install_kernel_from_tgz(file_path, auto_reboot, text_area): ...
# def burn_image_to_ssd(file_path, disk_name, text_area): ...

def main():
    """
    Main function to launch the GUI.
    """
    root = tk.Tk()
    app = NVMToolGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()