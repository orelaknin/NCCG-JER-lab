import subprocess
import os
import time
import re

def run_cmd(cmd, get_output=True):
    result = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=get_output, text=True)
    return result.stdout.strip() if get_output else None


def get_installed_kernels():
    # Run the exact bash command and write to temp file
    cmd = """bash -c 'grubby --info=ALL | grep title= | grep -oP "title=\\"\\\\K[^\\"]+" | sort > /tmp/my_present_kernel.txt'"""
    os.system(cmd)  # safer in this context than subprocess
    
    try:
        with open("/tmp/my_present_kernel.txt") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []



def get_boot_type():
    return "UEFI" if os.path.exists("/sys/firmware/efi") else "BIOS"

def print_banner():
    banner = """
 \033[01;32m  #######################################################################################################
 \033[01;32m  ######################### This tool commits any installed kernel on the OS. ###########################
 \033[01;32m  #######################################################################################################
 \033[01;32m  ## Changing a Kernel has risks of booting or crashing the OS. So make sure about what you are doing. ##
 \033[01;32m  #######################################################################################################
 \033[01;32m ########################################################################################################
 \033[0m
"""
    print(banner)

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
        print(f"❌ Failed to update /etc/default/grub: {e}")
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

def main():
    kernels = get_installed_kernels()
    if not kernels:
        print("No kernels found!")
        return

    print_banner()

    print(f"\033[01;32m Your running kernel is --->>>> \033[01;37m{os.uname().release}")
    print(f"\033[01;32m Your Boot type is --->>>> \033[01;37m{get_boot_type()}\033[0m\n")

    print("==============================================================================")
    print("These are the Kernel list installed on your system. Please select the option:")
    print("==============================================================================\n")

    for i, kernel in enumerate(kernels, start=1):
        print(f"{i}) {kernel}")

    while True:
        try:
            choice = int(input("\nEnter the number of your choice: "))
            if 1 <= choice <= len(kernels):
                selected_kernel = kernels[choice - 1]
                print(f"\nYou selected: {selected_kernel}")
                update_grub_default(selected_kernel)
                break
            else:
                print("Invalid option, try again.")
        except ValueError:
            print("Please enter a valid number.")

    rebuild_grub()

if __name__ == "__main__":
    main()
