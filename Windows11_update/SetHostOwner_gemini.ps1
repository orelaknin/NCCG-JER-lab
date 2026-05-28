# Get-HostOwner.ps1

<#
.SYNOPSIS
    Retrieves the host owner from a shared Excel file based on the hostname and stores it in the Windows Registry.

.DESCRIPTION
    This script connects to a specified Excel file, reads the hostname and owner information,
    finds the owner corresponding to the current machine's hostname, and then writes this
    owner's name to a custom registry key. This registry key can then be scanned by Lansweeper.

.PARAMETER ExcelFilePath
    The full UNC path to the shared Excel file (e.g., "\\\\YourServer\\Share\\HostOwners.xlsx").

.PARAMETER SheetName
    The name of the sheet within the Excel file that contains the host information (e.g., "Owners").

.PARAMETER HostnameColumn
    The letter of the column in the Excel file that contains the hostnames (e.g., "A").

.PARAMETER OwnerColumn
    The letter of the column in the Excel file that contains the owner names (e.g., "B").

.PARAMETER RegistryPath
    The full path to the registry key where the owner information will be stored
    (e.g., "HKLM:\\SOFTWARE\\YourCompany\\HostInfo").

.PARAMETER RegistryValueName
    The name of the registry value that will store the owner's name (e.g., "Owner").

.EXAMPLE
    .\Get-HostOwner.ps1 -ExcelFilePath "\\\\Server\\Share\\HostOwners.xlsx" `
                        -SheetName "Sheet1" `
                        -HostnameColumn "A" `
                        -OwnerColumn "B" `
                        -RegistryPath "HKLM:\\SOFTWARE\\MyCompany\\AssetInfo" `
                        -RegistryValueName "AssignedOwner"

.NOTES
    - Ensure the Excel file is accessible from the client machines.
    - The Excel file should have a header row. The script starts reading from the second row.
    - This script uses COM objects for Excel interaction, which requires Microsoft Excel to be installed on the machine
      where the script is executed.
    - Run this script with Administrator privileges if the target registry path is under HKLM.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$ExcelFilePath,

    [Parameter(Mandatory=$true)]
    [string]$SheetName,

    [Parameter(Mandatory=$true)]
    [string]$HostnameColumn,

    [Parameter(Mandatory=$true)]
    [string]$OwnerColumn,

    [Parameter(Mandatory=$true)]
    [string]$RegistryPath,

    [Parameter(Mandatory=$true)]
    [string]$RegistryValueName
)

# --- Configuration Variables (can be overridden by parameters) ---
# Example: "\\YourServer\Share\HostOwners.xlsx"
# Example: "Owners"
# Example: "A" (for Hostname)
# Example: "B" (for Owner)
# Example: "HKLM:\SOFTWARE\YourCompany\HostInfo"
# Example: "Owner"

# --- Script Logic ---

Write-Host "Starting host owner extraction process..."

# Get the current hostname
$currentHostname = $env:COMPUTERNAME
Write-Host "Current Hostname: $currentHostname"

# Initialize Excel COM object
$excel = $null
$workbook = $null
$worksheet = $null

try {
    Write-Host "Attempting to open Excel application..."
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false # Keep Excel hidden

    Write-Host "Opening Excel file: $ExcelFilePath"
    $workbook = $excel.Workbooks.Open($ExcelFilePath)
    $worksheet = $workbook.Sheets.Item($SheetName)

    if (-not $worksheet) {
        throw "Sheet '$SheetName' not found in the Excel file."
    }

    Write-Host "Searching for hostname in sheet '$SheetName'..."

    $foundOwner = $null
    $lastRow = $worksheet.UsedRange.Rows.Count

    # Loop through rows, starting from the second row (assuming header in first row)
    for ($row = 2; $row -le $lastRow; $row++) {
        $hostnameCell = $worksheet.Cells.Item($row, $HostnameColumn).Text
        $ownerCell = $worksheet.Cells.Item($row, $OwnerColumn).Text

        if ($hostnameCell -eq $currentHostname) {
            $foundOwner = $ownerCell
            Write-Host "Hostname '$currentHostname' found. Owner: $foundOwner"
            break # Exit loop once found
        }
    }

    if ($null -eq $foundOwner) {
        Write-Warning "Hostname '$currentHostname' not found in the Excel file. No owner will be written to the registry."
        # Optionally, you could write a "Not Found" or "Unknown" value to the registry here.
    } else {
        # Ensure the registry path exists
        Write-Host "Ensuring registry path '$RegistryPath' exists..."
        New-Item -Path $RegistryPath -Force -ErrorAction SilentlyContinue | Out-Null

        # Write the owner to the registry
        Write-Host "Writing owner '$foundOwner' to registry value '$RegistryValueName' at '$RegistryPath'..."
        Set-ItemProperty -Path $RegistryPath -Name $RegistryValueName -Value $foundOwner -Force

        Write-Host "Successfully wrote owner to registry."
    }

}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    Write-Error "Script execution failed."
}
finally {
    # Clean up Excel COM objects
    if ($workbook -ne $null) {
        $workbook.Close($false) # Close without saving changes
        $workbook = $null
    }
    if ($excel -ne $null) {
        $excel.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
        $excel = $null
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    Write-Host "Excel COM objects cleaned up."
}

Write-Host "Host owner extraction process completed."
