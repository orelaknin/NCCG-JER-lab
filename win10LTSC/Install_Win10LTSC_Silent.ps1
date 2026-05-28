# PowerShell script to install Windows 10 LTSC from mounted ISO silently
# Runs setup.exe from a mounted drive with silent installation parameters

# Define paths and variables
$logPath = "C:\Temp\Win10LTSC_Install.log"
$tempDir = "C:\Temp"
$minDiskSpaceGB = 20
$mountedDriveLetter = "" # Will auto-detect or specify like "D:"

# Function to write to log file
function Write-Log {
    param ($Message)
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [INFO] - $Message"
    Add-Content -Path $logPath -Value $logMessage
    Write-Output $logMessage
}

# Function to find mounted Windows 10 LTSC ISO
function Find-MountedSetup {
    Write-Log "Searching for mounted Windows 10 LTSC setup..."
    
    # Get all available drives
    $drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 }
    
    foreach ($drive in $drives) {
        $setupPath = "$($drive.Name):\setup.exe"
        if (Test-Path $setupPath) {
            # Check if it's a Windows installation media
            $sourcesPath = "$($drive.Name):\sources"
            if (Test-Path $sourcesPath) {
                Write-Log "Found Windows setup at $setupPath"
                return $setupPath
            }
        }
    }
    
    Write-Log "No mounted Windows setup found."
    return $null
}

# Function to check available disk space
function Test-DiskSpace {
    Write-Log "Checking available disk space..."
    $freeSpaceGB = [math]::Round((Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB, 2)
    
    if ($freeSpaceGB -ge $minDiskSpaceGB) {
        Write-Log "Available disk space: $freeSpaceGB GB (Requirement: $minDiskSpaceGB GB) - OK"
        return $true
    } else {
        Write-Log "Insufficient disk space: $freeSpaceGB GB available (Requirement: $minDiskSpaceGB GB)"
        return $false
    }
}

# Function to check current Windows version
function Get-CurrentWindowsVersion {
    $osInfo = Get-CimInstance Win32_OperatingSystem
    $version = $osInfo.Caption
    $build = $osInfo.BuildNumber
    Write-Log "Current OS: $version (Build: $build)"
    return @{
        Caption = $version
        Build = $build
    }
}

# Start logging
Write-Log "=== Windows 10 LTSC Silent Installation Script Started ==="

# Create temp directory if it doesn't exist
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Log "Created temp directory: $tempDir"
} else {
    Write-Log "Temp directory already exists: $tempDir"
}

# Get current Windows version
$currentOS = Get-CurrentWindowsVersion

# Check disk space
if (-not (Test-DiskSpace)) {
    Write-Log "Aborting installation due to insufficient disk space."
    Write-Host "Installation aborted: Not enough free disk space. Check $logPath for details."
    exit 1
}

# Find mounted setup
$setupPath = Find-MountedSetup

if (-not $setupPath) {
    Write-Log "No mounted Windows 10 LTSC installation media found."
    Write-Host "Error: Please mount the Windows 10 LTSC ISO first."
    Write-Host "Check $logPath for details."
    exit 1
}

# Verify setup.exe exists
if (-not (Test-Path $setupPath)) {
    Write-Log "Setup.exe not found at $setupPath"
    Write-Host "Setup file not found. Check $logPath for details."
    exit 1
}

# Run the installation silently
try {
    Write-Log "Starting Windows 10 LTSC installation from $setupPath..."
    Write-Log "Installation arguments: /auto upgrade /quiet"
    
    # Start the Windows setup process with silent parameters
    # /auto upgrade - Performs an upgrade installation
    # /quiet - Silent installation without user interaction
    # /noreboot - Prevents automatic reboot after installation
    # /DynamicUpdate disable - Disables dynamic updates during setup
    # /showoobe none - Skips OOBE (Out of Box Experience)
    
    $process = Start-Process -FilePath $setupPath `
        -ArgumentList "/auto upgrade /quiet" `
        -PassThru `
        -ErrorAction Stop

    Write-Log "Setup process started (PID: $($process.Id))"
    
    # Give it a moment to start
    Start-Sleep -Seconds 10

    # Try to find the setup process
    $setupProc = Get-Process -Name "setupprep", "setup" -ErrorAction SilentlyContinue

    if ($setupProc) {
        Write-Log "Detected Windows setup process (PID: $($setupProc.Id)). Monitoring installation..."

        # Wait for the setup process to complete
        $setupProc | ForEach-Object {
            Write-Log "Waiting for process $($_.ProcessName) (PID: $($_.Id)) to complete..."
            $_.WaitForExit()
        }

        Write-Log "Setup process exited. Waiting to ensure completion..."
        Start-Sleep -Seconds 5

        # Check if the process has restarted
        $setupProcRestarted = Get-Process -Name "setupprep", "setup" -ErrorAction SilentlyContinue
        if ($setupProcRestarted) {
            Write-Log "Setup process restarted (PID: $($setupProcRestarted.Id)). Waiting again..."
            $setupProcRestarted | ForEach-Object {
                $_.WaitForExit()
            }
        }

        Write-Log "Windows 10 LTSC installation completed. System ready for restart."
        Write-Host "Installation completed successfully. Please restart the computer to complete the setup."
        Write-Host "Log file: $logPath"
        
    } else {
        Write-Log "Could not detect setup process. It may have exited already or failed to launch."
        Write-Host "Setup may have launched and exited. Please verify on the system."
        Write-Host "Check $logPath for details."
    }

} catch {
    Write-Log "Error during installation process: $_"
    Write-Host "Error during installation. Check $logPath for details."
    exit 1
}

Write-Log "=== Script Completed ==="
