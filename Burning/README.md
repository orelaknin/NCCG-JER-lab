# NVM Burner & Kernel Installer

An integrated tool for flashing NVMe drives and installing kernel packages on Intel test systems.

## Features

### 🔥 Image Burning
- Flash OS images (.img, .iso, .bin, .raw) to NVMe drives
- Progress monitoring during flash operations
- Automatic drive detection

### 📦 Kernel Installation  
- Extract and install kernel packages from .tgz archives
- Automatic RPM detection and installation
- GRUB configuration updates
- UEFI boot support

### 🌐 Network Integration
- Connects to remote share for accessing images/kernels
- Browse and select files interactively
- Automatic file type detection

## Usage

### Interactive Mode
```bash
python3 nvm_burner.py
```

### Auto-reboot After Kernel Install
```bash
python3 nvm_burner.py --auto-reboot
```

## Workflow

1. **Connect**: Mounts remote share `//ladjsvop.jer.intel.com/burn`
2. **Detect**: Verifies NVMe drive presence (`/dev/nvme0n1`)
3. **Browse**: Interactive file/directory navigation
4. **Process**: Automatically handles:
   - `.tgz` files → Kernel installation
   - Image files → Drive flashing
5. **Cleanup**: Unmounts share and cleans temporary files

## File Type Detection

| Icon | Type | Action |
|------|------|--------|
| 📁 | Directory | Navigate deeper |
| 📦 | Kernel (.tgz) | Extract & install kernel |
| 💿 | Image (.img, .iso, etc.) | Flash to drive |
| 📄 | Other files | User choice |

## Requirements

- Linux system with UEFI boot mode
- sudo privileges
- Network access to Intel shares
- Python 3.6+
- Required packages: `cifs-utils`, `dnf`/`yum`

## Safety Notes

⚠️ **DESTRUCTIVE OPERATIONS**
- Image burning completely erases the target drive
- Kernel installation modifies boot configuration
- Always verify target drive before proceeding

## Supported Kernel Packages

The script looks for these RPM packages in extracted .tgz files:
- `kernel-*.rpm` (main kernel)
- `kernel-devel-*.rpm` (development headers)
- `kernel-headers-*.rpm` (kernel headers) 
- `kernel-modules-*.rpm` (kernel modules)
- `kernel-core-*.rpm` (core components)

## Examples

### Typical Workflow
1. Run script: `python3 nvm_burner.py`
2. Navigate to `Kernel` folder
3. Select a .tgz file (e.g., `mev-hw-c0-6.6.4-ci-release.11758.978-fedora37.tgz`)
4. Confirm kernel installation
5. Reboot when prompted

### Emergency Image Flash
1. Run script: `python3 nvm_burner.py`
2. Navigate to image location
3. Select .img/.iso file
4. Confirm flashing operation

## Integration Notes

This tool combines functionality from:
- Original `nvm_burner.py` (image flashing)
- `kernel_change.sh` (kernel installation)

The integration provides a unified interface for complete system deployment workflows.
