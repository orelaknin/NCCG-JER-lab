# PowerShell script to upgrade Windows 10 to Windows 11 on a user's PC
# Downloads Windows 11 Installation Assistant, performs silent upgrade with custom args, and completes without waiting for reboot

# Define paths and variables
$logPath = "C:\Temp\Win11Upgrade.log"
$tempDir = "C:\Temp"
$installerPath = "$tempDir\Windows11InstallationAssistant.exe"
$installerUrl = "https://go.microsoft.com/fwlink/?linkid=2171764" # Official Microsoft Windows 11 Installation Assistant URL
$minDiskSpaceGB = 20

# Function to write to log file
function Write-Log {
    param ($Message)
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [INFO] - $Message"
    Add-Content -Path $logPath -Value $logMessage
    Write-Output $logMessage
}

# Function to check hardware compatibility for Windows 11
function Test-Win11Compatibility {
    Write-Log "Checking hardware compatibility for Windows 11..."
    $tpmCheck = (Get-WmiObject -Namespace "root\cimv2\security\microsofttpm" -Class Win32_Tpm -ErrorAction SilentlyContinue).IsEnabled
    $cpuCheck = (Get-WmiObject Win32_Processor).Name -match "Intel|AMD"
    $ramCheck = (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB -ge 4
    $diskSpaceCheck = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB -ge $minDiskSpaceGB

    if ($tpmCheck -and $cpuCheck -and $ramCheck -and $diskSpaceCheck) {
        Write-Log "Hardware is compatible for Windows 11 upgrade."
        return $true
    } else {
        Write-Log "Hardware compatibility check failed: TPM=$tpmCheck, CPU=$cpuCheck, RAM=$ramCheck, DiskSpace=$diskSpaceCheck"
        return $false
    }
}

# Start logging
Write-Log "Windows 11 upgrade script started."

# Create temp directory if it doesn't exist
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Log "Created temp directory: $tempDir"
} else {
    Write-Log "Temp directory already exists: $tempDir"
}

# Check hardware compatibility
if (-not (Test-Win11Compatibility)) {
    Write-Log "Aborting upgrade due to incompatible hardware."
    Write-Host "Upgrade aborted: Your PC does not meet Windows 11 requirements. Check $logPath for details."
    exit 1
}

# Download Windows 11 Installation Assistant
try {
    Write-Log "Downloading Windows 11 Installation Assistant from $installerUrl..."
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($installerUrl, $installerPath)
    $fileSize = [math]::Round((Get-Item -Path $installerPath).Length / 1MB, 2)
    Write-Log "Downloaded Windows 11 Installation Assistant to $installerPath ($fileSize MB)."
} catch {
    Write-Log "Failed to download installer: $_"
    Write-Host "Failed to download installer. Check $logPath for details."
    exit 1
}

# Verify downloaded file exists
if (-not (Test-Path $installerPath)) {
    Write-Log "Installer not found at $installerPath."
    Write-Host "Installer not found. Check $logPath for details."
    exit 1
}

# Run the upgrade silently
try {
    Write-Log "Starting Windows 11 upgrade process..."

    # Start the Windows 11 Installation Assistant
    $process = Start-Process -FilePath $installerPath -ArgumentList "/QuietInstall /Auto Upgrade /NoReboot /SkipEULA" -PassThru -ErrorAction Stop

    # Give it a moment to start the real upgrade process
    Start-Sleep -Seconds 10

    # Try to find the actual upgrade process
    $upgradeProc = Get-Process -Name "Windows10UpgraderApp*" -ErrorAction SilentlyContinue

    if ($upgradeProc) {
        Write-Log "Detected Windows10UpgraderApp process (PID: $($upgradeProc.Id)). Waiting for it to complete..."

        # Wait for the real upgrade process to complete
        $upgradeProc.WaitForExit()

        Write-Log "Upgrade process exited. Waiting to ensure no relaunch occurs..."
        Start-Sleep -Seconds 8

        # Check if the process has restarted
        $upgradeProcRestarted = Get-Process -Name "Windows10UpgraderApp*" -ErrorAction SilentlyContinue
        if ($upgradeProcRestarted) {
            Write-Log "Upgrade process restarted (PID: $($upgradeProcRestarted.Id)). Waiting again..."
            $upgradeProcRestarted.WaitForExit()
        }

        Write-Log "Upgrade process completed. Awaiting user restart."
        Write-Host "Upgrade completed. User will be prompted to restart manually."
    } else {
        Write-Log "Could not detect Windows10UpgraderApp. It may have exited already or failed to launch."
        Write-Host "Upgrade may have launched and exited early. Verify on the target system."
    }

} catch {
    Write-Log "Error during upgrade process: $_"
    Write-Host "Error during upgrade. Check $logPath for details."
    exit 1
}
