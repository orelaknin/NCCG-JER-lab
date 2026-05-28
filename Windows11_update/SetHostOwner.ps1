# SetHostOwner.ps1
# Connects to a shared Excel file, extracts the owner based on hostname, and stores it in the registry

# Define variables
$excelFilePath = "\\ladjitfstech\Lansweeper_win10_to_11\win11_09_07_SCRIPT.xlsx"  
$registryPath = "HKLM:\SOFTWARE\Lansweeper\Custom"
$registryValueName = "Owner"
$worksheetName = "report"  
$hostname = $env:COMPUTERNAME
$modulePath = "\\ladjitfstech.ger.corp.intel.com\Lansweeper_win10_to_11\Modules"

try {
    # Import the ImportExcel module from the package share
    Import-Module -Name "$modulePath\ImportExcel" -ErrorAction Stop

    # Read the Excel file
    $excelData = Import-Excel -Path $excelFilePath -WorksheetName $worksheetName

    # Find the owner for the current hostname (case-insensitive match)
    $owner = $excelData | Where-Object { $_.Hostname -ieq $hostname } | Select-Object -ExpandProperty Owner

    if ($owner) {
        # Ensure the registry path exists
        if (-not (Test-Path $registryPath)) {
            New-Item -Path $registryPath -Force | Out-Null
        }

        # Write the owner to the registry
        Set-ItemProperty -Path $registryPath -Name $registryValueName -Value $owner -Type String -Force

        Write-Host "Successfully set owner '$owner' for hostname '$hostname' in registry."
    } else {
        Write-Warning "No owner found for hostname '$hostname' in the Excel file."
    }
} catch {
    Write-Error "Error: $_"
    exit 1
}